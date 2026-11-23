import pytest

from app.services.device_identity import normalize_mac_address


@pytest.mark.parametrize(
    "value",
    [
        "aa:bb:cc:dd:ee:ff",
        "AA-BB-CC-DD-EE-FF",
        "aabbccddeeff",
        "  aA:bB:cC:dD:eE:fF  ",
    ],
)
def test_normalize_mac_address_returns_canonical_format(value):
    assert normalize_mac_address(value) == "AA:BB:CC:DD:EE:FF"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "AA:BB:CC:DD:EE",
        "AA:BB:CC:DD:EE:GG",
        "AA-BB:CC-DD-EE-FF",
        "AA::BB:CC:DD:EE:FF",
        None,
    ],
)
def test_normalize_mac_address_rejects_invalid_input(value):
    with pytest.raises(ValueError, match="^Invalid device MAC address$"):
        normalize_mac_address(value)

def test_lookup_resolves_only_the_observed_hotspot_host(monkeypatch):
    from app.services import device_identity

    class Router:
        def path(self, *name):
            return {
                ("system", "identity"): [{"name": "CHR"}],
                ("ip", "hotspot"): [
                    {"name": "lab", "interface": "ether4", "profile": "WEZA-Hotspot"},
                ],
                ("ip", "hotspot", "host"): [
                    {"server": "lab", "address": "10.20.0.254", "mac-address": "8a:aa:52:95:b9:bb"},
                    {"server": "other", "address": "10.20.0.253", "mac-address": "8a:aa:52:95:b9:bc"},
                ],
            }[name]

        def close(self):
            pass

    monkeypatch.setattr(device_identity, "connect_router", Router)
    monkeypatch.setattr(device_identity, "router_settings", lambda: {"expected_identity": "CHR"})
    assert device_identity.resolve_hotspot_device("10.20.0.254") == "8A:AA:52:95:B9:BB"
    with pytest.raises(ValueError, match="No unique hotspot device"):
        device_identity.resolve_hotspot_device("10.20.0.253")


def test_device_reference_is_expiring_and_cannot_authenticate_staff(monkeypatch):
    from app.core import security

    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    claims = {"user": 1, "package": 2, "key": "checkout-123", "ip": "10.20.0.254", "mac": "8A:AA:52:95:B9:BB"}
    reference = security.create_device_reference(claims)
    assert security.read_device_reference(reference)["mac"] == claims["mac"]
    assert security.read_token(reference) is None
    monkeypatch.setattr(security.time, "time", lambda: 1)
    expired = security.create_device_reference(claims)
    with pytest.raises(ValueError, match="expired"):
        security.read_device_reference(expired)
