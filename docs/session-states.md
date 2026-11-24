# Wi-Fi session states

A successful payment creates at most one session. Payment status and
activation status are tracked separately: a router problem never changes a
payment that M-Pesa confirmed (WEZA-51).

## Purchase and payment

A purchase stays `pending` until a payment succeeds, then becomes `paid`.
A failed payment attempt leaves the purchase pending so the customer can try
again with a new payment attempt.

## Session lifecycle

The session starts at `PAYMENT_CONFIRMED` with activation status
`not_started` and no timer. Activation records an attempt and moves the
session through `ACTIVATING`. When the router confirms, the session becomes
`ACTIVE` with activation status `succeeded`, and `started_at` and
`expires_at` are set. The duration is the one captured at purchase time.

A failed activation moves the session to `FAILED` with activation status
`failed` and leaves the timer unset. Another activation attempt is allowed
from `FAILED`. Repeating activation after success returns the existing
session and its original timestamps; the router is not called again.

## Allowed (status, activation_status) pairs

| status | activation_status | Meaning | Timer fields |
| --- | --- | --- | --- |
| `PAYMENT_CONFIRMED` | `not_started` | Session exists, router not asked yet | empty |
| `ACTIVATING` | `waiting` | An attempt is in flight, or the router gave no clear answer (see below) | empty |
| `ACTIVE` | `succeeded` | Router confirmed access; the clock started at that moment | `started_at`, `expires_at` set |
| `FAILED` | `failed` | Router refused or an error occurred; `failure_reason` is set | empty |

The database enforces that `started_at` and `expires_at` can only be set
when `activation_status = 'succeeded'` (`ck_sessions_timer_needs_activation`).
The customer's time can never start before the router confirms.

The model reserves `PENDING_PAYMENT`, `EXPIRED` and `CANCELLED` for future
flows. The fulfilment code does not set them.

```
PAYMENT_CONFIRMED / not_started
        |  activate_session
        v
ACTIVATING / waiting ---- router confirms ----> ACTIVE / succeeded
        |
        |---- router refuses or errors -------> FAILED / failed
        |---- router gives no clear answer ---> stays ACTIVATING / waiting

FAILED / failed ---- another activation attempt ----> ACTIVATING / waiting
```

Any other starting state makes `activate_session` raise `ValueError`, which
`fulfil_payment` reports as `not_attempted`.

## Who changes what

| Step | Code | Changes |
| --- | --- | --- |
| Callback verified and committed | `settle_payment` | `payments.status`, `purchases.status` |
| Session created | `create_session` | inserts the session as `PAYMENT_CONFIRMED` / `not_started` |
| Router asked for access | `activate_session` | session status, activation status, timer fields, one `activation_attempts` row |
| Outcome classified | `fulfil_payment` | nothing; it only reads the session and returns an outcome |

`fulfil_payment` never raises and never touches the payment. It runs only
after a freshly applied success. A duplicate callback does NOT run it again,
so a retry after a failed activation is always deliberate (WEZA-63), never a
side effect of Safaricom resending the callback.

## The "unconfirmed" marker

There is no `unconfirmed` activation status. When the router result is
unclear, the session stays `ACTIVATING` / `waiting`, and the ONLY marker is
the latest `activation_attempts` row: `error_code =
'RouterActivationUnconfirmed'` with `status` still `started`. Treat this as
"access may or may not be applied". Calling `activate_session` again
reconciles it with a verify-only router call (MikroTik mode only). Never
create a new attempt for an unconfirmed one.

## Outcomes returned by `fulfil_payment`

| Outcome | Session after | Payment |
| --- | --- | --- |
| `activated` | `ACTIVE` / `succeeded` | unchanged (`successful`) |
| `activation_failed` | `FAILED` / `failed` | unchanged |
| `activation_unconfirmed` | `ACTIVATING` / `waiting` | unchanged |
| `not_attempted` | no session created or changed | unchanged |
| `unexpected_error` | unknown; check logs | unchanged |

## Guarantees and how they are enforced

* One session per payment: `UNIQUE sessions.payment_id`.
* One in-flight attempt per session: partial unique index
  `uq_one_started_attempt`.
* Simultaneous fulfilments: the session row is locked in `activate_session`.
  `fulfil_payment` expires its cached session first, so the caller that lost
  the race reloads the winner's result instead of acting on stale data.
  Covered by `tests/test_fulfilment_concurrency.py`.

## Pending and known gaps

Not built yet: expiry enforcement, disconnection, payment recovery
(WEZA-63), and hotspot or PPPoE policy.

* The router is called inside an open transaction while the session row is
  locked. A crash after the router applied access but before the commit
  rolls back to `PAYMENT_CONFIRMED` while the customer is online.
* A crash between the settlement commit and fulfilment leaves a successful
  payment with no session. WEZA-63 must find and recover these.
* A session can stay `ACTIVATING` after a crash. WEZA-63 must recover it.
* `activate_session` loads the session with a lock but without
  `populate_existing`, so a concurrent caller can act on stale data. Only
  the CHECK constraint stops it. Worked around in `fulfil_payment`; the
  proper fix belongs to WEZA-54.
* `failure_reason` stores up to 255 characters of router error text shown
  to staff. It might contain hostnames or usernames.
* Live-mode guards (block mock payments, require a verified device) apply
  only in MikroTik mode. In mock mode a purchase without a device still
  activates against the mock.
* Session statuses are plain strings; there is no enum.
* There is no lock timeout: a second worker waits while a slow router call
  holds the row lock.
* The router call delays the callback reply and holds the request's
  database session. A background task would be the proper fix.
  