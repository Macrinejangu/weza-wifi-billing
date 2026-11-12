# API contracts

## GET /health

No request parameters. HTTP 200 returns JSON `{"status":"ok"}` when the FastAPI process responds. This endpoint checks API liveness only. See [the database guide](database-decision.md) to verify the migration separately.

OpenAPI is available at `/docs` and `/openapi.json` on the local backend. Record future endpoint contracts, error responses, and payment and session states here under WEZA-61 before wiring the frontend.
