import pytest

from app.services import hotspot_device_lookup as lookup


CLIENT_IP = "10.20.0.254"
HOTSPOT_SERVER = "WEZA-Hotspot-server"
ROUTER_IDENTITY = "WEZA-Test-Router"


def host_record(**overrides):
    return {
        "server": HOTSPOT_SERVER,
        "address": CLIENT_IP,
        "mac-address": "8a:aa:52:95:b9:bb",
        **overrides,
    }


class FakeRouter:
    def __init__(self):
        self.identity = ROUTER_IDENTITY
        self.hosts = [host_record()]
        self.closed = False
        self.paths_read = []

    def path(self, *parts):
        self.paths_read.append(parts)
        if parts == ("system", "identity"):
            return [{"name": self.identity}]
        if parts == ("ip", "hotspot", "host"):
            return self.hosts
        raise AssertionError(f"Unexpected RouterOS path: {parts}")

    def close(self):
        self.closed = True


@pytest.fixture
def router(monkeypatch):
    fake = FakeRouter()
    monkeypatch.setattr(lookup, "connect_router", lambda: fake)
    return fake


def resolve_device():
    return lookup.lookup_hotspot_device(
        CLIENT_IP,
        expected_router_identity=ROUTER_IDENTITY,
        expected_hotspot_server=HOTSPOT_SERVER,
    )


def test_returns_device_from_expected_hotspot(router):
    router.hosts.append(host_record(server="Other-Hotspot"))

    assert resolve_device() == lookup.HotspotDevice(
        mac_address="8A:AA:52:95:B9:BB",
        ip_address=CLIENT_IP,
        hotspot_server=HOTSPOT_SERVER,
    )
    assert router.closed


def test_rejects_unknown_ip_on_expected_hotspot(router):
    router.hosts = [
        host_record(address="10.20.0.253"),
        host_record(server="Other-Hotspot"),
    ]

    with pytest.raises(lookup.HotspotDeviceNotFound):
        resolve_device()

    assert router.closed


def test_rejects_multiple_matches_on_expected_hotspot(router):
    router.hosts.append(host_record(**{"mac-address": "02:11:22:33:44:55"}))

    with pytest.raises(lookup.HotspotDeviceNotFound):
        resolve_device()

    assert router.closed


def test_rejects_wrong_router_before_reading_hosts(router):
    router.identity = "Other-Router"

    with pytest.raises(
        lookup.HotspotLookupUnavailable,
        match="Router identity could not be verified",
    ):
        resolve_device()

    assert router.paths_read == [("system", "identity")]
    assert router.closed