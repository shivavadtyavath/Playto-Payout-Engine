"""
Payout state machine.

Legal transitions:
    pending    → processing
    processing → completed
    processing → failed

All other transitions are illegal and raise InvalidTransitionError.

Design decision: We use a dictionary-based transition map rather than a
class hierarchy or enum-based approach. This makes the legal transitions
explicit, readable, and easy to audit. The check happens before any DB
write, so an illegal transition never touches the database.
"""
from django.utils.timezone import now

# The single source of truth for legal state transitions.
# Any transition not in this map is illegal.
VALID_TRANSITIONS: dict[str, list[str]] = {
    'pending':     ['processing'],
    'processing':  ['completed', 'failed'],
    'completed':   [],   # terminal state
    'failed':      [],   # terminal state
}


class InvalidTransitionError(Exception):
    """Raised when a payout state transition is not in VALID_TRANSITIONS."""
    pass


def transition_payout(payout, new_state: str) -> None:
    """
    Transition a payout to a new state.

    Raises InvalidTransitionError if the transition is not legal.
    Updates status and updated_at atomically via save(update_fields=...).

    NOTE: This function does NOT handle fund returns on failure.
    The caller (Celery task) is responsible for creating the credit
    LedgerEntry within the same atomic() block.
    """
    allowed = VALID_TRANSITIONS.get(payout.status, [])
    if new_state not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition payout {payout.id} from '{payout.status}' to '{new_state}'. "
            f"Legal transitions from '{payout.status}': {allowed}"
        )
    payout.status = new_state
    payout.updated_at = now()
    payout.save(update_fields=['status', 'updated_at'])
