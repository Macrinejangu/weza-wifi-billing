
import app.services.router as router_service


def test_connect_router_without_ssl(monkeypatch):
    settings = {
        "host": "192.0.2.10",
        "username": "test-user",
        "password": "test-password",
        "port": 8728,
        "timeout": 5,
        "use_ssl": False,
        "tls_ca_file": None,
        "tls_server_name": "192.0.2.10",
        "expected_identity": "CHR",
    }

    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return "fake-api"

    monkeypatch.setattr(router_service, "router_settings", lambda: settings)
    monkeypatch.setattr(router_service, "connect", fake_connect)

    result = router_service.connect_router()

    assert result == "fake-api"
    assert captured["host"] == "192.0.2.10"
    assert captured["port"] == 8728
    assert "ssl_wrapper" not in captured


def test_connect_router_with_verified_ssl(monkeypatch):
    settings = {
        "host": "router.example.test",
        "username": "test-user",
        "password": "test-password",
        "port": 8729,
        "timeout": 5,
        "use_ssl": True,
        "tls_ca_file": "/tmp/router-ca.pem",
        "tls_server_name": "router.example.test",
        "expected_identity": "CHR",
    }

    captured = {}

    class FakeSSLContext:
        def wrap_socket(self, sock, server_hostname=None):
            captured["socket"] = sock
            captured["server_hostname"] = server_hostname
            return "verified-tls-socket"

    fake_context = FakeSSLContext()

    def fake_create_default_context(cafile=None):
        captured["cafile"] = cafile
        return fake_context

    def fake_connect(**kwargs):
        captured["connect_kwargs"] = kwargs
        return "fake-api"

    monkeypatch.setattr(router_service, "router_settings", lambda: settings)
    monkeypatch.setattr(
        router_service.ssl,
        "create_default_context",
        fake_create_default_context,
    )
    monkeypatch.setattr(router_service, "connect", fake_connect)

    result = router_service.connect_router()

    assert result == "fake-api"
    assert captured["cafile"] == "/tmp/router-ca.pem"

    ssl_wrapper = captured["connect_kwargs"]["ssl_wrapper"]
    wrapped_socket = ssl_wrapper("fake-socket")

    assert wrapped_socket == "verified-tls-socket"
    assert captured["socket"] == "fake-socket"
    assert captured["server_hostname"] == "router.example.test"
    assert captured["connect_kwargs"]["port"] == 8729
