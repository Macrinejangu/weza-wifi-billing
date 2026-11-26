# API contracts

FastAPI publishes the full request and response schemas at `/docs` and `/openapi.json`.

Staff payment recovery routes are described in [payment recovery](payment-recovery.md).

`GET /api/payments` and `GET /api/payments/{payment_id}` return the payment `status` and a separate `access_status` to signed-in staff. Access is `unconfirmed`, `activating`, `active`, `failed`, `expired` or `ended`. `session_id` identifies the session for this payment when one exists. Staff can use it to find the corresponding record in Sessions.

## Foundation API

- `GET /health` returns HTTP 200 with `{"status":"ok"}`. This checks whether the API process responds.
- `GET /api/packages/` returns HTTP 200 with the active packages, including their ID, name, service type, price in whole Kenyan shillings, duration in minutes, download and upload speeds in Mbps, description and active flag.

## Local activation demo

Use a local PostgreSQL database migrated with `python -m alembic upgrade head` from `backend/`. Set `ENABLE_MOCK_PAYMENTS=true` only in the local demo environment and use fixture users and phone numbers. The demo routes return HTTP 404 when disabled.

Set a unique random `JWT_SECRET` in the root `.env` and run `python -m app.create_staff` from `backend/` to create a staff account.

Package management is independent of the payment mode. Staff can read the complete catalogue with `GET /api/packages/staff`. Creation, editing and deactivation require an administrator token from `POST /api/auth/login`. Public package viewing shows only active packages. Package changes are recorded in the staff audit log. Existing purchases keep their saved package terms.

| Request | Required input | Success response |
| --- | --- | --- |
| `POST /api/packages/` | `name`, `service_type`, positive integer `price`, `duration_minutes`, `download_speed_mbps` and `upload_speed_mbps`. Optional `description`. | 200 and the created package. |
| `PUT /api/packages/{package_id}` | Same fields as creation, plus boolean `is_active`. | 200 and the updated package. |
| `DELETE /api/packages/{package_id}` | Package ID in the path. | 200 and `{"message":"Package deactivated"}`. |
| `POST /api/purchases` | Integer `user_id` and `package_id`. The `Idempotency-Key` header takes 8 to 100 characters. | 201 with `id`, `amount`, `package_name`, `duration_minutes` and `status`. Repeating the same request with the same key returns the existing purchase with 200. |
| `POST /api/payments/mock` | Integer `purchase_id` and `phone_number` as `254` followed by nine digits. Optional boolean `successful` defaults to true. | 200 with `id`, `status` and nullable `mpesa_receipt_number`. |
| `POST /api/sessions` | Integer `payment_id`. Optional `device_mac_address` and `device_ip_address`. | 201 with a session for the confirmed payment. |
| `POST /api/sessions/{session_id}/activate` | Session ID in the path and a staff bearer token. | 200 when active, with timer timestamps. 202 while router confirmation is pending, with `activation_status` set to `waiting`. |
| `GET /api/sessions/{session_id}` | Session ID in the path and a staff bearer token. | 200 with the session details. |

For session activation and detail, send the token from `POST /api/auth/login` in the `Authorization: Bearer <token>` header. Missing, invalid, or expired tokens and suspended staff accounts receive 401. Active customers receive 403. Authorized staff receive 404 for a missing session.

Session responses include `id`, `status`, `activation_status`, `failure_reason`, `started_at` and `expires_at`. See [session states](session-states.md) for transitions.

Invalid input returns 422 with validation details. Missing records or inactive packages at purchase creation return 404 with a `detail` message. Reusing a purchase key for a different request, paying a non-pending purchase, or creating a session for an unconfirmed payment returns 400 with a `detail` message. A failed router simulation returns 502 and records the failed activation attempt.

## Customer registration and guided support

- `POST /api/auth/customer/register` accepts `full_name`, `email`, `phone`, and `password`. A new customer receives 201 and signs in at `POST /api/auth/customer/login`. The route creates customer accounts only and returns 409 for duplicate account details.
- `GET /api/support/faqs` returns public help topics and their answer steps.
- `PUT /api/support/faqs/{faq_id}` accepts `question` and `steps` from an authenticated administrator. Successful edits return the saved answer and appear in the staff audit log.

## Authenticated customer checkout

- `POST /api/customer/purchases` requires a customer bearer token, an `Idempotency-Key`
  header, and a JSON body with `package_id`. The server sets the owner from the token.
  A new purchase returns 201. A repeat of the same request returns 200.
- `GET /api/customer/payments/{payment_id}` requires a customer bearer token.
  Returns the stored payment ID, purchase ID, status, amount, package name, and
  M-Pesa receipt for confirmed payments. Missing payments and payments owned by
  another customer both return 404. This endpoint does not contact Daraja and
  remains available with payment initiation disabled.

## POST /api/payments

Asks Daraja (sandbox) to send an M-Pesa prompt to the customer's phone for one purchase. Implemented in WEZA-49.

The route returns 404 by default. Set `ENABLE_DARAJA_SANDBOX_PAYMENTS=true` only in a sandbox restricted to the team. The switch enables the route independently of the Daraja credentials, so both the switch and valid sandbox settings are required to send a prompt.

**Accepted by Daraja does not mean paid.** A 201 only means the prompt was sent. The payment stays `pending` until a verified callback or status query settles it (WEZA-50).

### Request

Send the customer bearer token in the Authorization header. The purchase must belong to that customer.

```json
{"purchase_id": 12, "phone_number": "0712345678"}
```

| Field | Rules |
| --- | --- |
| `purchase_id` | Positive integer. The purchase must exist and be pending. |
| `phone_number` | Safaricom mobile number. Stored and sent as `254XXXXXXXXX`. |

There is no `amount` field. The amount always comes from the stored purchase, so a client cannot choose the price. Any extra field is ignored.

### Success: 201

```json
{
  "payment_id": 7,
  "purchase_id": 12,
  "amount": 20,
  "status": "pending",
  "message": "Check your phone and enter your M-Pesa PIN to complete the payment."
}
```

`amount` is whole shillings. The response never contains the phone number.

### Errors

Every error from this endpoint has this body, which differs from the plain `{"detail": ...}` errors of the earlier endpoints above. `payment_id` appears only when a payment row exists.

```json
{"detail": "Purchase not found.", "code": "purchase_not_found", "payment_id": 7}
```

| HTTP | `code` | Meaning | Payment row afterwards |
| --- | --- | --- | --- |
| 404 | `purchase_not_found` | No such purchase. | none |
| 409 | `purchase_not_payable` | Purchase is not pending (paid, failed or expired). | none |
| 409 | `payment_already_pending` | A payment is already pending for this purchase (double tap). Use the returned `payment_id`. | existing one, unchanged |
| 502 | `provider_rejected` | Daraja refused the request. Daraja's own codes are never shown to clients. | `failed` |
| 503 | `provider_not_reached` | No prompt was sent (for example, no access token). | `failed` |
| 502 / 504 | `outcome_unknown` | Daraja answered oddly, was down, or timed out (504). A prompt may have been sent. | stays `pending` |
| 503 | `payments_not_configured` | Daraja settings are missing on the server. | none |
| 503 | `service_unavailable` | Database unavailable. | none |
| 500 | `internal_error` | Our own bug. The text is generic by design. | see note |
| 422 | (FastAPI validation body) | Malformed request. Raised before any payment code runs. | none |

Note on `internal_error`: the payment, if one was created, is marked `failed`.

The client must never create a second payment after `outcome_unknown`. The first attempt may still be answered by the customer, so it is resolved by the status query, not by a retry.

### Payment states

| Status | Meaning | Set by |
| --- | --- | --- |
| `pending` | Prompt sent or possibly sent, no verified result yet. | WEZA-49 |
| `successful` | Verified payment. Only verified provider data sets this. | WEZA-50 |
| `failed` | Proven not sent, refused, cancelled or failed. | WEZA-49, WEZA-50 |
| `expired` | Pending too long with no answer. | WEZA-50 |

Payment status is separate from activation status. `successful` never means the internet is active.

### Known gaps

- There is no customer login yet. Anyone who guesses a purchase id could trigger a prompt for it. An ownership check is needed once customer authentication exists.
- Device verification before the prompt (WEZA-53) is not wired in yet.

## POST /api/payments/mpesa/callback/{token}

Receives Daraja's STK Push result. Implemented in WEZA-50. Called by Safaricom, never by our frontends, and hidden from `/docs`.

### Protection

Callbacks are not signed, so the endpoint relies on these checks, in this order:

1. Optional source-IP allowlist (`CALLBACK_IP_CHECK_ENABLED`, off by default).
2. A secret token in the URL path (`DARAJA_CALLBACK_TOKEN`). `DARAJA_CALLBACK_URL` must end with the same token.
3. A body size limit of 64 KB.
4. The callback must match a payment we created: both request IDs, the amount and the phone number.
5. Success and failure are both confirmed with the STK status query before the payment changes. Unknown or failed queries leave the payment `pending`.

A wrong IP, a wrong token and an unconfigured endpoint all get the same empty 404.

### Responses

| HTTP | Meaning |
| --- | --- |
| 200 | The message was stored and handled. Also returned for messages we rejected, because Safaricom cannot act on our reasons. Body: `{"ResultCode": 0, "ResultDesc": "Accepted"}`. |
| 404 | IP, token or configuration check failed. Empty body. |
| 413 | Body over 64 KB or a bad `Content-Length`. Nothing is stored. |
| 503 | The message could not be recorded (database down). |
| 500 | Our own bug. Generic body, and the audit event stays `received`. |

### Audit trail

Every accepted message is saved in `payment_events` before processing and ends as `applied`, `duplicate`, `rejected` or `unmatched`. A duplicate delivery changes nothing.

### Replay a stored callback

If a callback arrives before initiation saves the provider request IDs, its audit event is marked `unmatched`. If a matching callback cannot be confirmed because Daraja's query is inconclusive, the event records that reason. An authorized backend operator with access to the sandbox configuration and database can replay the original callback event:

```sh
cd backend
python -m app.replay_mpesa_callback EVENT_ID
```

Replay uses the stored callback, repeats the same verification and status query, and records a separate audit event linked to the original event ID in the payload. It sends no STK prompt. Run it once the initiation IDs are saved or the query service has recovered. The original audit row stays intact. Repeat replay cannot settle an already successful payment twice. Automated reconciliation is separate.

If no callback arrived, an authorized operator with the sandbox settings can
check a pending payment directly using its saved Daraja reference:

```sh
cd backend
python -m app.recheck_mpesa_payment PAYMENT_ID
```

The command sends no new payment prompt. It records the query result and
marks a verified failure as failed. A paid query alone does not include the
receipt needed to grant access, so the payment remains pending for review.

Only a freshly committed successful payment starts access fulfilment.
Duplicate, failed and unverified notifications do not run activation again.
An activation exception cannot undo the payment or change the normal provider
acknowledgement. A paid purchase without confirmed access appears in the staff
issues list. Staff may retry access from that list without sending another
payment prompt.

Uvicorn access log entries for callback paths are suppressed. Configure proxy, tunnel and hosting access logs to omit or redact the secret path before exposing the route.

### Unverified (not confirmed from official Daraja pages)

- The official STK Push page we checked does not state what reply the endpoint must return. We return 200 with the JSON above.
- Only result codes 0 and 1032 are official. Other codes map to `unknown`.
- The 12 callback IPs have not been tested against the sandbox, so the IP check stays off by default.
- Whether the sandbox sends callbacks to a tunnel URL has not been tested.
