# API contracts

FastAPI publishes the full request and response schemas at `/docs` and `/openapi.json`.

## Foundation API

- `GET /health` returns HTTP 200 with `{"status":"ok"}`. This checks whether the API process responds.
- `GET /api/packages/` returns HTTP 200 with the active packages, including their ID, name, service type, price in whole Kenyan shillings, duration in minutes, download and upload speeds in Mbps, description and active flag.

## Local activation demo

Use a local PostgreSQL database migrated with `python -m alembic upgrade head` from `backend/`. Set `ENABLE_MOCK_PAYMENTS=true` only in the local demo environment and use fixture users and phone numbers. The demo routes return HTTP 404 when disabled.

Set a unique random `JWT_SECRET` in the root `.env` and run `python -m app.create_staff` from `backend/` to create a staff account.

Package creation, editing, and deactivation also require a bearer token from `POST /api/auth/login`. Send the token in the `Authorization` header. An active customer receives HTTP 403. Missing, invalid, or expired tokens and suspended staff receive HTTP 401. Public package viewing stays available.

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

## POST /api/payments

Asks Daraja (sandbox) to send an M-Pesa prompt to the customer's phone for one purchase. Implemented in WEZA-49.

**Accepted by Daraja does not mean paid.** A 201 only means the prompt was sent. The payment stays `pending` until a verified callback or status query settles it (WEZA-50).

### Request

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