"""
Celery tasks for payout processing.

Task hierarchy:
  process_pending_payouts (beat, every 10s)
    └── process_payout (per payout)

  retry_stuck_payouts (beat, every 30s)
    ├── retry_payout (for stuck payouts with retry_count < 3)
    │     └── process_payout (re-enqueued after reset to pending)
    └── force_fail_payout (for stuck payouts with retry_count >= 3)

Concurrency safety in tasks:
  Every task that modifies a payout uses SELECT FOR UPDATE to prevent
  two workers from processing the same payout simultaneously.
  The early-return guard (if payout.status != expected_state: return)
  ensures idempotency at the task level.
"""
import random
import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils.timezone import now

from .models import Payout
from .state_machine import transition_payout, InvalidTransitionError
from ledger.models import LedgerEntry

logger = logging.getLogger(__name__)


@shared_task(name='payouts.tasks.process_pending_payouts')
def process_pending_payouts():
    """
    Dispatcher task: find all pending payouts and enqueue individual processing tasks.
    Runs every 10 seconds via Celery beat.
    """
    payout_ids = list(
        Payout.objects.filter(status=Payout.PENDING).values_list('id', flat=True)
    )
    logger.info("process_pending_payouts: found %d pending payouts", len(payout_ids))
    for payout_id in payout_ids:
        process_payout.delay(str(payout_id))


@shared_task(name='payouts.tasks.process_payout')
def process_payout(payout_id: str):
    """
    Process a single payout through the bank settlement simulation.

    Outcomes (weighted random):
      70% → completed
      20% → failed  (funds returned atomically)
      10% → hung    (stays in processing; retry_stuck_payouts will pick it up)
    """
    # Step 1: Transition pending → processing (with lock to prevent double-processing)
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(id=payout_id)
        except Payout.DoesNotExist:
            logger.error("process_payout: payout %s not found", payout_id)
            return

        if payout.status != Payout.PENDING:
            # Already picked up by another worker or in a terminal state
            logger.info(
                "process_payout: payout %s is in state '%s', skipping",
                payout_id, payout.status
            )
            return

        try:
            transition_payout(payout, Payout.PROCESSING)
        except InvalidTransitionError as e:
            logger.error("process_payout: invalid transition for %s: %s", payout_id, e)
            return

    # Step 2: Simulate bank settlement (outside the lock — simulates network latency)
    outcome = random.choices(
        ['completed', 'failed', 'hung'],
        weights=[70, 20, 10],
        k=1
    )[0]

    logger.info("process_payout: payout %s outcome=%s", payout_id, outcome)

    if outcome == 'completed':
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != Payout.PROCESSING:
                return
            try:
                transition_payout(payout, Payout.COMPLETED)
            except InvalidTransitionError as e:
                logger.error("process_payout: completed transition failed for %s: %s", payout_id, e)

    elif outcome == 'failed':
        # CRITICAL: fund return must be atomic with state transition.
        # If the transaction rolls back, neither the credit nor the status change persists.
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != Payout.PROCESSING:
                return
            try:
                transition_payout(payout, Payout.FAILED)
            except InvalidTransitionError as e:
                logger.error("process_payout: failed transition failed for %s: %s", payout_id, e)
                return

            # Return funds to merchant balance via credit ledger entry
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type=LedgerEntry.CREDIT,
                amount_paise=payout.amount_paise,
                description=f'Refund for failed payout {payout_id}',
                payout=payout,
            )
            logger.info(
                "process_payout: refunded %d paise to merchant %s for failed payout %s",
                payout.amount_paise, payout.merchant_id, payout_id
            )

    # outcome == 'hung': do nothing — retry_stuck_payouts will handle it


@shared_task(name='payouts.tasks.retry_stuck_payouts')
def retry_stuck_payouts():
    """
    Find payouts stuck in 'processing' for more than 30 seconds and retry or force-fail them.
    Runs every 30 seconds via Celery beat.

    Retry logic:
      retry_count < 3  → reset to pending and re-process (exponential backoff: 2^retry_count seconds)
      retry_count >= 3 → force-fail and return funds
    """
    cutoff = now() - timedelta(seconds=30)

    # Payouts eligible for retry
    retryable = Payout.objects.filter(
        status=Payout.PROCESSING,
        updated_at__lt=cutoff,
        retry_count__lt=3,
    )
    for payout in retryable:
        delay_seconds = 2 ** payout.retry_count  # 1s, 2s, 4s
        logger.info(
            "retry_stuck_payouts: scheduling retry for payout %s (retry_count=%d, delay=%ds)",
            payout.id, payout.retry_count, delay_seconds
        )
        retry_payout.apply_async(args=[str(payout.id)], countdown=delay_seconds)

    # Payouts that have exhausted all retries
    exhausted = Payout.objects.filter(
        status=Payout.PROCESSING,
        updated_at__lt=cutoff,
        retry_count__gte=3,
    )
    for payout in exhausted:
        logger.info(
            "retry_stuck_payouts: force-failing payout %s (retry_count=%d)",
            payout.id, payout.retry_count
        )
        force_fail_payout.delay(str(payout.id))


@shared_task(name='payouts.tasks.retry_payout')
def retry_payout(payout_id: str):
    """
    Reset a stuck payout back to pending and re-enqueue for processing.
    Increments retry_count before resetting.
    """
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(id=payout_id)
        except Payout.DoesNotExist:
            logger.error("retry_payout: payout %s not found", payout_id)
            return

        if payout.status != Payout.PROCESSING:
            logger.info(
                "retry_payout: payout %s is in state '%s', skipping",
                payout_id, payout.status
            )
            return

        payout.retry_count += 1
        payout.status = Payout.PENDING
        payout.save(update_fields=['status', 'retry_count', 'updated_at'])
        logger.info(
            "retry_payout: reset payout %s to pending (retry_count=%d)",
            payout_id, payout.retry_count
        )

    # Re-enqueue for processing
    process_payout.delay(payout_id)


@shared_task(name='payouts.tasks.force_fail_payout')
def force_fail_payout(payout_id: str):
    """
    Force-fail a payout that has exhausted all retries.
    Atomically transitions to failed and returns funds to merchant.
    """
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(id=payout_id)
        except Payout.DoesNotExist:
            logger.error("force_fail_payout: payout %s not found", payout_id)
            return

        if payout.status != Payout.PROCESSING:
            logger.info(
                "force_fail_payout: payout %s is in state '%s', skipping",
                payout_id, payout.status
            )
            return

        try:
            transition_payout(payout, Payout.FAILED)
        except InvalidTransitionError as e:
            logger.error("force_fail_payout: transition failed for %s: %s", payout_id, e)
            return

        # Return funds atomically with state transition
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            entry_type=LedgerEntry.CREDIT,
            amount_paise=payout.amount_paise,
            description=f'Refund for force-failed payout {payout_id} (max retries exceeded)',
            payout=payout,
        )
        logger.info(
            "force_fail_payout: force-failed payout %s, refunded %d paise to merchant %s",
            payout_id, payout.amount_paise, payout.merchant_id
        )
