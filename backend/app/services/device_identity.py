import os
import re
from ipaddress import ip_address

from dotenv import load_dotenv

from app.config import ROOT_ENV, router_settings
from app.services.router import HOTSPOT_INTERFACE, HOTSPOT_PROFILE, connect_router

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


def checkout_device_verification_enabled() -> bool:
    load_dotenv(ROOT_ENV)
    return os.getenv("ENABLE_DIRECT_HOTSPOT_CHECKOUT", "false").lower() == "true"


def resolve_hotspot_device(client_ip: str) -> str:
    """Resolve a direct connection to one host on the configured hotspot."""
    expected = router_settings()["expected_identity"]
    if not expected:
        raise RuntimeError("Expected hotspot router identity is not configured")

    api = connect_router()
    try:
        identities = list(api.path("system", "identity"))
        if len(identities) != 1 or identities[0].get("name") != expected:
            raise RuntimeError("Hotspot router identity does not match")

        servers = [
            server["name"] for server in api.path("ip", "hotspot")
            if server.get("interface") == HOTSPOT_INTERFACE
            and server.get("profile") == HOTSPOT_PROFILE
            and server.get("disabled") not in (True, "true", "yes")
            and server.get("invalid") not in (True, "true", "yes")
            and server.get("name")
        ]
        if len(servers) != 1:
            raise RuntimeError("Expected one enabled hotspot server")

        hosts = [
            host for host in api.path("ip", "hotspot", "host")
            if host.get("server") == servers[0] and host.get("address") == client_ip
        ]
        if len(hosts) != 1:
            raise ValueError("No unique hotspot device for this connection")
        return normalize_mac_address(hosts[0].get("mac-address"))
    finally:
        api.close()


def validate_client_ip(value: str) -> str:
    address = ip_address(value)
    if address.version != 4 or address.is_loopback or address.is_unspecified:
        raise ValueError("Checkout requires a direct IPv4 hotspot connection")
    return str(address)
