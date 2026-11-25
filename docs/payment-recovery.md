# Payment recovery (WEZA-63)

Staff routes for a customer who paid but is not connected, and for a payment that never got an answer. Payment status and activation status stay separate: a router problem never changes a payment that M-Pesa confirmed. None of these routes sends a payment prompt.

## Routes

Without a valid staff token the cases and retry routes return 401.

| Request | What it does |
| --- | --- |
| `GET /api/recovery/cases` | Lists unresolved cases, without raw provider text. |
| `GET /api/recovery/cases/{payment_id}` | Returns one case. |
| `POST /api/recovery/cases/{payment_id}/retry` | Runs fulfilment again for a confirmed payment, against the same payment and session. It never contacts Daraja. |
| `POST /api/recovery/cases/{payment_id}/check-payment` | Asks Daraja for the status of one pending payment, using its saved checkout request ID. |

A retry returns 200 with an `outcome`: `activated`, `activation_failed`, `activation_unconfirmed`, `not_attempted` or `unexpected_error`. A retry that cannot help is refused with 409 and a fixed `code`: `nothing_to_retry` (already connected) or `needs_staff_review`. Each accepted retry is written to the staff audit log before the router is called ("Retried payment activation").

A status check reports one of `settled`, `already_settled`, `still_pending`, `rejected` or `no_answer`. Errors: 404 for an unknown payment, 409 with `payment_not_open` or `no_checkout_request_id` when the payment cannot be checked, 503 with `daraja_not_configured`, and 503 when the database is unavailable. Each check is written to the audit log ("Checked payment status with M-Pesa").

## How a status query settles a payment

- Only a PAID answer settles the payment. FAILED, unknown and Daraja errors leave it `pending`.
- The query reply carries no amount, phone number or receipt. A payment settled this way has no M-Pesa receipt number and no callback time. `paid_at` is the moment we confirmed it.
- Fulfilment then runs as for a callback. It needs `ROUTER_MODE` set to `mock` or `mikrotik`. In MikroTik mode the purchase must also have a verified device MAC address.
- This differs from `python -m app.recheck_mpesa_payment`, which records a PAID query but leaves the payment pending.

## Sweeper

`sweep_stale_payments` checks pending payments older than 10 minutes, at most 20 per run (the maximum is 100), and settles them by the rules above. It is not scheduled: no command or cron job calls it yet.

## Paid time

Paid time runs from `paid_at`. Recovery only works while package time remains. For a payment older than its package, the recovery retry reports `not_attempted` or `needs_staff_review`, and `POST /api/connection-issues/{payment_id}/retry` returns 409.

## Unverified (not confirmed from official Daraja pages)

- The STK query path in `client.py` (`/mpesa/stkpushquery/v1/query`) and how a still-processing payment is reported. Only a sandbox test can confirm them.
- The comment in `client.py` that an in-progress query arrives as HTTP 5xx.

## Known gaps

- Pending payments with no checkout request ID are listed as stale but cannot be checked or swept.
- A query-only FAILED answer leaves the payment pending for staff review.
- The sweeper has no schedule.
- A paid customer whose package time has passed cannot be reconnected.
