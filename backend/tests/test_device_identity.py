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