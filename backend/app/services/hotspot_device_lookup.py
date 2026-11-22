from dataclasses import dataclass
from ipaddress import IPv4Address

from app.services.device_identity import normalize_mac_address
from app.services.router import connect_router


class HotspotDeviceNotFound(LookupError):
    """The expected hotspot has no unique device for the observed IP."""


class HotspotLookupUnavailable(RuntimeError):
    """The expected router could not be reached or verified."""


@dataclass(frozen=True)
class HotspotDevice:
    mac_address: str
    ip_address: str
    hotspot_server: str


def lookup_hotspot_device(
    observed_ip: str,
    *,
    expected_router_identity: str,
    expected_hotspot_server: str,
) -> HotspotDevice:
    """Resolve an IPv4 address from trusted request context to a hotspot host."""
    if not isinstance(observed_ip, str):
        raise ValueError("Invalid device IP address")
    try:
        client_ip = str(IPv4Address(observed_ip))
    except ValueError as error:
        raise ValueError("Invalid device IP address") from error

    if not expected_router_identity.strip() or not expected_hotspot_server.strip():
        raise HotspotLookupUnavailable("Hotspot lookup is not configured")

    try:
        api = connect_router()
        try:
            identities = list(api.path("system", "identity"))
            if (
                len(identities) != 1
                or identities[0].get("name") != expected_router_identity
            ):
                raise HotspotLookupUnavailable("Router identity could not be verified")

            matches = [
                host
                for host in api.path("ip", "hotspot", "host")
                if host.get("server") == expected_hotspot_server
                and host.get("address") == client_ip
            ]
        finally:
            api.close()
    except HotspotLookupUnavailable:
        raise
    except Exception as error:
        raise HotspotLookupUnavailable("Hotspot lookup is unavailable") from error

    if len(matches) != 1:
        raise HotspotDeviceNotFound("No unique matching hotspot device")

    reported_mac = matches[0].get("mac-address")
    try:
        mac_address = normalize_mac_address(
            reported_mac if isinstance(reported_mac, str) else ""
        )
    except ValueError as error:
        raise HotspotLookupUnavailable("Router returned an invalid device MAC") from error

    return HotspotDevice(
        mac_address=mac_address,
        ip_address=client_ip,
        hotspot_server=expected_hotspot_server,
    )