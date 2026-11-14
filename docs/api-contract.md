# API contracts

## GET /health

No request parameters. HTTP 200 returns JSON `{"status":"ok"}` when the FastAPI process responds. This endpoint checks API liveness only. See [the database guide](database-decision.md) to verify the migration separately.

OpenAPI is available at `/docs` and `/openapi.json` on the local backend. Record future endpoint contracts, error responses, and payment and session states here under WEZA-61 before wiring the frontend.

API Endpoints

Method Endpoint Purpose
GET /api/packages Retrieve available Wi-Fi packages.
POST /api/payments/mock Simulate a customer payment.
POST /api/sessions Create a session after payment verification.
GET /api/sessions/{session_id} Retrieve session status and expiry.
POST /api/sessions/{session_id}/disconnect Disconnect an active session.

Standard HTTP Responses

- 200 OK – Request successful.
- 201 Created – Resource created.
- 400 Bad Request – Invalid request.
- 404 Not Found – Resource not found.
- 500 Internal Server Error – Server error.

Request and response schemas will be defined during endpoint implementation.
