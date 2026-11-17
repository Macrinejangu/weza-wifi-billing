
import asyncio

from httpx import ASGITransport, AsyncClient

import app.api.router as router_api
from app.main import app


def request_router_status(headers=None):
    async def make_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(
                "/router/status",
                headers=headers,
            )

    return asyncio.run(make_request())


def test_router_status_with_valid_key(monkeypatch):
    monkeypatch.setattr(
        router_api,
        "weza_api_key",
        lambda: "test-secret-key",
    )
    monkeypatch.setattr(
        router_api,
        "get_router_identity",
        lambda: {"name": "CHR"},
    )

    response = request_router_status(
        {"X-WEZA-API-Key": "test-secret-key"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "connected",
        "identity": "CHR",
    }


def test_router_status_without_key(monkeypatch):
    monkeypatch.setattr(
        router_api,
        "weza_api_key",
        lambda: "test-secret-key",
    )

    response = request_router_status()

    assert response.status_code == 401


def test_router_status_with_invalid_key(monkeypatch):
    monkeypatch.setattr(
        router_api,
        "weza_api_key",
        lambda: "test-secret-key",
    )

    response = request_router_status(
        {"X-WEZA-API-Key": "wrong-key"}
    )

    assert response.status_code == 401


def test_router_status_when_router_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        router_api,
        "weza_api_key",
        lambda: "test-secret-key",
    )

    def unavailable_router():
        raise OSError("Router connection failed")

    monkeypatch.setattr(
        router_api,
        "get_router_identity",
        unavailable_router,
    )

    response = request_router_status(
        {"X-WEZA-API-Key": "test-secret-key"}
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Router is unavailable"
    }
