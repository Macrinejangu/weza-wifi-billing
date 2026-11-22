import re

_MAC_PATTERN = re.compile(
    r"(?:[0-9a-f]{12}|(?:[0-9a-f]{2}:){5}[0-9a-f]{2}|"
    r"(?:[0-9a-f]{2}-){5}[0-9a-f]{2})",
    re.IGNORECASE | re.ASCII,
)


def normalize_mac_address(value: str) -> str:
    """Validate MAC address syntax and return uppercase colon-separated pairs."""
    if not isinstance(value, str):
        raise ValueError("Invalid device MAC address")

    address = value.strip()
    if _MAC_PATTERN.fullmatch(address) is None:
        raise ValueError("Invalid device MAC address")

    digits = address.replace(":", "").replace("-", "").upper()
    return ":".join(digits[index : index + 2] for index in range(0, 12, 2))