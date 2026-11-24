# Wi-Fi session states

The paid subscription starts when the system confirms payment. It ends at
that timestamp plus the duration saved on the purchase. Activation status
is separate. Opening the status page, retrying activation or reconnecting
does not reset the timer.

| Session status | What it means |
| --- | --- |
| `PAYMENT_CONFIRMED` | Payment succeeded. The customer is waiting for access. |
| `ACTIVATING` | An activation attempt is in progress or the router outcome is uncertain. |
| `ACTIVE` | The access provider confirmed the grant. Connection status is distinct from handset browsing. |
| `FAILED` | Access was not confirmed. The payment remains successful. Staff can retry an unexpired paid purchase from Connection Issues. |
| `EXPIRED` | Its time ended and the expiry process completed the relevant cleanup. |

A confirmed payment can appear in Connection Issues even if a session was
never created. Staff retry uses the saved purchase and never sends another
payment prompt. For uncertain router outcomes it verifies the existing
attempt before assuming a grant succeeded.

Run `python -m app.expire_sessions` from `backend/` for the pilot. A failed
router disconnection is recorded and remains eligible for retry.
WEZA_EXPIRY_INTERVAL_SECONDS and WEZA_EXPIRY_BATCH_SIZE configure the worker. The process
only revokes a router grant whose ownership it can verify. An older router
user without a recorded grant needs manual review. When running against a
test database, use `ROUTER_MODE=mock` and keep Daraja disabled.

The older mock-only session APIs still support the legacy test path with
an activation-based session timer. Use the customer simulated checkout to
rehearse the pilot's payment-based timer.
