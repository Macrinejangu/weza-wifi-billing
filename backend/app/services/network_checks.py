"""Read-only checks of provisioned network equipment."""

import ipaddress
import shutil
import subprocess
import sys

from app.config import router_settings
from app.services.router import HOTSPOT_INTERFACE, HOTSPOT_PROFILE, connect_router

PRIVATE_MANAGEMENT_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
)


def ping_target(address: str | None) -> str | None:
    if not address:
        return None
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return None
    if "%" in str(parsed) or not any(parsed in subnet for subnet in PRIVATE_MANAGEMENT_NETWORKS):
        return None
    return str(parsed)


def ping_device(address: str) -> str:
    use_ipv6 = ipaddress.ip_address(address).version == 6
    binary = shutil.which("ping6" if use_ipv6 and sys.platform == "darwin" else "ping")
    if not binary:
        return "unavailable"
    protocol = ["-6"] if use_ipv6 and sys.platform != "darwin" else []
    try:
        result = subprocess.run(
            [binary, *protocol, "-n", "-c", "1", "-W", "1000" if sys.platform == "darwin" else "1", address],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False,
        )
    except subprocess.TimeoutExpired:
        return "no_response"
    except OSError:
        return "unavailable"
    if result.returncode == 0:
        return "reachable"
    if result.returncode == (2 if sys.platform == "darwin" else 1):
        return "no_response"
    return "unavailable"


def read_gateway() -> tuple[str, bool]:
    expected = router_settings()["expected_identity"]
    if not expected:
        raise RuntimeError("Expected router identity is required")
    api = connect_router()
    try:
        identities = list(api.path("system", "identity"))
        if len(identities) != 1 or identities[0].get("name") != expected:
            raise RuntimeError("Router identity could not be verified")
        hotspots = [row for row in api.path("ip", "hotspot")
                    if row.get("interface") == HOTSPOT_INTERFACE and row.get("profile") == HOTSPOT_PROFILE]
        if len(hotspots) != 1:
            raise RuntimeError("Could not identify one Weza hotspot")
        disabled = hotspots[0].get("disabled")
        if disabled in (True, "true", "yes"):
            return expected, False
        if disabled in (False, "false", "no"):
            return expected, True
        raise RuntimeError("Hotspot state could not be verified")
    finally:
        api.close()
