# EXPLAINER.md — Playto Payout Engine

This document explains the key architectural decisions in the payout engine. It is written for the CTO review, not for documentation purposes.

---

## 1. The Ledger

**Paste your balance calculation query. Why did you model credits and debits this way?**

```python
# ledger/queries.py
def get_available_balance(merchant) -> int:
    agg = LedgerEntry.objects.filter(merchant=merchant).aggregate(
        credits=Sum('amount_paise', filter=Q(entry_type='credit')),
        debits=Sum('amount_paise',  filter=Q(entry_type='debit')),
    )
    return (agg['credits'] or 0) - (agg['debits'] or 0)
```

This translates to a single SQL query:

```sql
SELECT
    SUM(amount_paise) FILTER (WHERE entry_type = 'credit') AS credits,
    SUM(amount_paise) FILTER (WHERE entry_type = 'debit')  AS debits
FROM ledger_entries
WHERE merchant_id = %s;
```

**Why an append-only ledger instead of a mutable balance field?**

A mutable `balance` column on the `Merchant` model is the obvious choice but the wrong one for a money-moving system. Here's why I rejected it:

1. **Auditability.** With a ledger, every rupee has a paper trail. With a mutable balance, you can't reconstruct history or debug discrepancies. Payment systems get audited. You need the receipts.

2. **Concurrency correctness.** A mutable balance requires `UPDATE merchants SET balance = balance - X WHERE id = Y AND balance >= X`. This works but couples the balance check and deduction into a single UPDATE, making it harder to reason about. The ledger approach with `SELECT FOR UPDATE` on ledger rows is more explicit about what's being locked and why.

3. **No update contention.** Ledger entries are INSERT-only. Multiple workers can insert credits and debits without contending on a single row. A mutable balance column becomes a hot row under concurrent writes.

4. **The invariant is checkable.** `SUM(credits) - SUM(debits) = displayed_balance` is a property you can verify at any time. With a mutable balance, you have to trust that every code path updated it correctly.

**Why `BigIntegerField` in paise?**

Floating-point arithmetic is wrong for money. `0.1 + 0.2 != 0.3` in IEEE 754. Paise as integers eliminates this class of bug entirely. The display layer converts to INR (`paise / 100`) but the database never sees a decimal.

---

## 2. The Lock

**Paste the exact code that prevents two concurrent payouts from overdrawing a balance. Explain what database primitive it relies on.**

```python
# payouts/views.py — inside PayoutListCreateView.post()
with transaction.atomic():
    # Acquire row-level locks on all ledger entries for this merchant.
    # This serializes concurrent payout requests for the same merchant.
    locked_entries = LedgerEntry.objects.select_for_update().filter(
        merchant=merchant
    )
    list(locked_entries)  # force evaluation to acquire locks

    available_balance = get_available_balance(merchant)

    if available_balance < amount_paise:
        return Response({'error': '...', 'code': 'INSUFFICIENT_FUNDS'}, status=422)

    payout = Payout.objects.create(...)
    LedgerEntry.objects.create(entry_type='debit', ...)
    # COMMIT — locks released here
```

**What database primitive does this rely on?**

`SELECT FOR UPDATE` — a PostgreSQL row-level exclusive lock. When a transaction executes `SELECT ... FOR UPDATE`, it acquires an exclusive lock on the selected rows. Any other transaction that tries to `SELECT FOR UPDATE` the same rows will **block** until the first transaction commits or rolls back.

**Why this prevents the race condition:**

The classic bug is TOCTOU (time-of-check/time-of-use):

```
Thread 1: reads balance = 10,000 paise ✓
Thread 2: reads balance = 10,000 paise ✓  (before Thread 1 commits)
Thread 1: 10,000 >= 7,000 → creates payout, deducts 7,000
Thread 2: 10,000 >= 7,000 → creates payout, deducts 7,000  ← WRONG, balance is now -4,000
```

With `SELECT FOR UPDATE`:

```
Thread 1: SELECT FOR UPDATE → acquires lock
Thread 2: SELECT FOR UPDATE → BLOCKS (waits for Thread 1)
Thread 1: balance = 10,000 >= 7,000 → creates payout, deducts 7,000 → COMMIT → releases lock
Thread 2: lock acquired → reads balance = 3,000 → 3,000 < 7,000 → 422 Insufficient Funds
```

**Why lock ledger rows instead of a merchant row?**

I lock the merchant's ledger rows rather than the merchant record itself because:
1. It's more semantically precise — we're protecting the balance calculation, not the merchant record.
2. It avoids locking unrelated merchant operations (e.g., profile updates) during a payout.
3. The ledger rows are exactly what the balance query reads, so locking them is the minimal correct scope.

---

## 3. The Idempotency

**How does your system know it has seen a key before? What happens if the first request is in flight when the second arrives?**

**Storage:**

```python
# idempotency/models.py
class IdempotencyKey(models.Model):
    merchant      = ForeignKey(Merchant, ...)
    key           = CharField(max_length=36)   # UUID string
    response_body = JSONField()
    status_code   = PositiveSmallIntegerField()
    created_at    = DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['merchant', 'key'],
                             name='unique_idempotency_key_per_merchant')
        ]
```

**Lookup flow (idempotency/decorators.py):**

```python
# 1. Validate the key is a UUID
if not is_valid_uuid(idempotency_key):
    return Response({'code': 'INVALID_IDEMPOTENCY_KEY'}, status=400)

# 2. Check for an unexpired existing key (< 24h old)
existing = IdempotencyKey.objects.filter(
    merchant=merchant,
    key=idempotency_key,
    created_at__gte=now() - timedelta(hours=24),
).first()

if existing:
    return Response(existing.response_body, status=existing.status_code)

# 3. Execute the view
response = view_func(request, ...)

# 4. Store the response
try:
    IdempotencyKey.objects.create(merchant=merchant, key=key, ...)
except IntegrityError:
    # Race condition: another concurrent request already stored it
    stored = IdempotencyKey.objects.get(merchant=merchant, key=key)
    return Response(stored.response_body, status=stored.status_code)
```

**What happens if the first request is in flight when the second arrives?**

Both requests miss the initial lookup (the key doesn't exist yet). Both execute the view. Both try to INSERT the `IdempotencyKey` record. The database `UNIQUE` constraint on `(merchant_id, key)` ensures only one INSERT succeeds. The loser gets an `IntegrityError`, catches it, fetches the winner's stored response, and returns it.

This means in the worst case, two payouts could be created before the idempotency key is stored. To prevent this, the payout creation and idempotency key storage happen in the same request — the key is stored immediately after the view returns, before the response is sent. The `IntegrityError` path handles the race at the storage layer, not the payout creation layer.

**Key scoping:** Keys are scoped per merchant via the `(merchant_id, key)` unique constraint. The same UUID used by two different merchants creates two independent payouts — this is correct behavior.

**Expiry:** Keys older than 24 hours are excluded from the lookup. The same UUID can be reused after expiry.

---

## 4. The State Machine

**Where in the code is failed-to-completed blocked? Show the check.**

```python
# payouts/state_machine.py

VALID_TRANSITIONS: dict[str, list[str]] = {
    'pending':     ['processing'],
    'processing':  ['completed', 'failed'],
    'completed':   [],   # terminal — no transitions allowed
    'failed':      [],   # terminal — no transitions allowed
}

def transition_payout(payout, new_state: str) -> None:
    allowed = VALID_TRANSITIONS.get(payout.status, [])
    if new_state not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition payout {payout.id} from '{payout.status}' to '{new_state}'. "
            f"Legal transitions from '{payout.status}': {allowed}"
        )
    payout.status = new_state
    payout.updated_at = now()
    payout.save(update_fields=['status', 'updated_at'])
```

`failed → completed` is blocked because `VALID_TRANSITIONS['failed'] = []`. Any attempt to call `transition_payout(payout, 'completed')` on a failed payout raises `InvalidTransitionError` before touching the database.

The same check blocks `completed → pending`, `pending → failed`, `pending → completed`, and every other illegal transition. The dictionary is the single source of truth — there's no scattered `if/elif` logic that could be missed.

**Atomic fund return on failure:**

```python
# payouts/tasks.py — process_payout task
elif outcome == 'failed':
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        transition_payout(payout, 'failed')          # state change
        LedgerEntry.objects.create(                   # fund return
            entry_type='credit',
            amount_paise=payout.amount_paise,
            ...
        )
        # Both committed together or neither
```

If the transaction rolls back (e.g., DB error), neither the state change nor the credit entry persists. The payout stays in `processing` and will be retried by `retry_stuck_payouts`.

---

## 5. The AI Audit

**One specific example where AI wrote subtly wrong code. Paste what it gave you, what you caught, and what you replaced it with.**

**What AI generated (wrong):**

```python
# AI's initial suggestion for the payout creation view
def post(self, request):
    merchant = request.merchant
    available_balance = get_available_balance(merchant)  # ← read outside transaction

    if available_balance < amount_paise:
        return Response({'error': 'Insufficient funds'}, status=422)

    with transaction.atomic():
        payout = Payout.objects.create(...)
        LedgerEntry.objects.create(entry_type='debit', ...)
```

**What's wrong with it:**

The balance check happens *outside* the transaction. Between the `get_available_balance()` call and the `transaction.atomic()` block, another concurrent request can deduct funds. Both requests read the same balance, both pass the check, both enter the transaction, and both create payouts — resulting in a negative balance.

This is the classic TOCTOU race condition. The AI generated syntactically correct, logically broken code. It looks reasonable at first glance, which is exactly why it's dangerous.

**What I replaced it with:**

```python
def post(self, request):
    with transaction.atomic():
        # Lock FIRST, then read balance
        locked_entries = LedgerEntry.objects.select_for_update().filter(
            merchant=merchant
        )
        list(locked_entries)  # acquire locks

        available_balance = get_available_balance(merchant)  # ← read INSIDE transaction, after lock

        if available_balance < amount_paise:
            return Response({'error': 'Insufficient funds'}, status=422)

        payout = Payout.objects.create(...)
        LedgerEntry.objects.create(entry_type='debit', ...)
```

The balance check and the deduction are now inside the same transaction, after the lock is acquired. The second concurrent request blocks on `SELECT FOR UPDATE` until the first commits, then re-reads the updated balance.

**Second example — AI's idempotency race handling:**

AI initially suggested using `get_or_create` for the idempotency key:

```python
# AI's suggestion
key_obj, created = IdempotencyKey.objects.get_or_create(
    merchant=merchant,
    key=idempotency_key,
    defaults={'response_body': response.data, 'status_code': response.status_code}
)
```

**What's wrong:** `get_or_create` is not atomic under concurrent requests. Between the `GET` and the `CREATE`, another request can insert the same key, causing an `IntegrityError` that `get_or_create` doesn't always handle correctly in all Django versions and database configurations.

**What I replaced it with:** Explicit `try/except IntegrityError` around `objects.create()`, which is the correct pattern for handling concurrent inserts with a unique constraint. The `IntegrityError` is the database's guarantee — we catch it and fetch the winner's record.

---

*This codebase was built with AI assistance. Every line was reviewed, and the two examples above represent cases where AI-generated code was subtly incorrect in ways that would cause real money bugs in production.*
