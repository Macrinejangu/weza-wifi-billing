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

## Authenticated customer checkout

- `POST /api/customer/purchases` requires a customer bearer token, an `Idempotency-Key`
  header, and a JSON body with `package_id`. The server sets the owner from the token.
  A new purchase returns 201. A repeat of the same request returns 200.
- `GET /api/customer/payments/{payment_id}` requires a customer bearer token.
  Returns the stored payment ID, purchase ID, status, amount, package name, and
  M-Pesa receipt for confirmed payments. Missing payments and payments owned by
  another customer both return 404. This endpoint does not
  