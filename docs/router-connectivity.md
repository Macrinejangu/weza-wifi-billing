# MikroTik Router Connectivity

## 1. Purpose

WEZA uses the MikroTik RouterOS API to verify connectivity
with an authorized test router.

The backend uses the `librouteros` Python library to
communicate with MikroTik routers.

Standard API connections and certificate-verified
API-SSL connections are supported.

## 2. Configuration

Router settings are loaded from the repository-root `.env`
file through `backend/app/config.py`.

Required settings for a verified router connection:

- ROUTER_HOST
- ROUTER_USERNAME
- ROUTER_PASSWORD
- EXPECTED_ROUTER_IDENTITY

API authentication:

- WEZA_API_KEY

Optional router settings:

- ROUTER_PORT (default: 8728)
- ROUTER_TIMEOUT (default: 5 seconds)
- ROUTER_USE_SSL (default: false)
- ROUTER_TLS_CA_FILE
- ROUTER_TLS_SERVER_NAME

Never commit the real `.env` file or router credentials.

## 3. Lab Testing

The lab configuration uses the standard MikroTik API
on TCP port 8728, with TLS disabled.

This connection is intended for an isolated development
network. Do not expose it over an untrusted network.

Router API access should be restricted to the authorized
backend IP address.

## 4. Production Security

The backend supports TLS through Python's SSL context
and the `librouteros` SSL wrapper.

For production deployment:

- Enable MikroTik API-SSL on port 8729.
- Configure a trusted TLS certificate on the router.
- Configure the appropriate trusted CA certificate.
- Verify the router certificate and hostname.
- Restrict API access to trusted backend addresses.
- Store router credentials in environment secrets.
- Use a private network or VPN where possible.

Certificate verification must never be disabled.

The TLS configuration has automated tests, but a live
production certificate-verified connection has not yet
been demonstrated.

## 5. Router Verification

The backend retrieves the MikroTik system identity.

A successful connection alone does not prove that the
intended router was reached.

WEZA compares the returned router identity against
EXPECTED_ROUTER_IDENTITY.

Missing or mismatched identities are rejected.

## 6. API Authentication

The `/router/status` endpoint requires the
`X-WEZA-API-Key` request header.

Implemented behavior:

- Missing client API key: HTTP 401.
- Invalid client API key: HTTP 401.
- Missing server-side API key configuration: HTTP 503.
- Missing expected router identity configuration: HTTP 503.
- Router unavailable: HTTP 503.
- Missing router identity: HTTP 502.
- Mismatched router identity: HTTP 502.
- Valid authentication and verified router: HTTP 200.

## 7. Testing

Run backend tests from the backend directory:

```bash
python -m pytest -q
```

Automated router tests use mocked connections and do not
require a physical MikroTik router.

Live router testing must only use an authorized
development router.

## 8. Live Connectivity Verification

A live connectivity test was successfully performed
against the authorized MikroTik CHR development router.

Test environment:

- Router model: MikroTik CHR
- RouterOS version: 7.24.6 Long-term
- Router identity: CHR
- API protocol: Standard RouterOS API
- API port: 8728
- TLS: Disabled for isolated lab testing
- Test execution environment: Windows Python virtual environment
- Backend: WEZA FastAPI

Verified results:

- Router API authentication succeeded.
- Router identity was retrieved successfully.
- GET /health returned HTTP 200.
- GET /router/status returned HTTP 200.
- Router status response confirmed the identity CHR.

Environment limitation:

The router was reachable from Windows but direct
connectivity from WSL was unsuccessful during testing.
The WSL networking issue remains unresolved.

Production API-SSL connectivity with a trusted
certificate has not yet been demonstrated.
