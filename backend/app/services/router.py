import time
import ipaddress
import re
import ssl
from decimal import Decimal, InvalidOperation

from librouteros import connect

from app.config import router_settings


HOTSPOT_INTERFACE = "ether4"
HOTSPOT_PROFILE = "WEZA-Hotspot"


class RouterActivationError(RuntimeError):
    """Raised when MikroTik cannot safely activate a Hotspot device."""


def connect_router():
    settings = router_settings()

    connection_options = {
        "host": settings["host"],
        "username": settings["username"],
        "password": settings["password"],
        "port": settings["port"],
        "timeout": settings["timeout"],
    }

    if settings["use_ssl"]:
        context = ssl.create_default_context(
            cafile=settings["tls_ca_file"]
        )

        def verified_tls_wrapper(sock):
            return context.wrap_socket(
                sock,
                server_hostname=settings["tls_server_name"],
            )

        connection_options["ssl_wrapper"] = verified_tls_wrapper

    return connect(**connection_options)


def get_router_identity() -> dict:
    api = connect_router()

    try:
        identity = list(api.path("system", "identity"))
        return identity[0] if identity else {}
    finally:
        api.close()


def _normalize_mac(mac_address: str) -> str:
    """Validate and normalize a MAC address for RouterOS MAC authentication."""
    if not isinstance(mac_address, str):
        raise ValueError("A valid device MAC address is required")

    compact_mac = re.sub(r"[:-]", "", mac_address.strip())

    if not re.fullmatch(r"[0-9A-Fa-f]{12}", compact_mac):
        raise ValueError("Invalid device MAC address")

    return ":".join(
        compact_mac[index:index + 2]
        for index in range(0, 12, 2)
    ).upper()


def _validate_speed(speed: int, field_name: str) -> int:
    if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
        raise ValueError(f"{field_name} must be a positive integer")

    return speed


def _rate_component_to_bps(value: str) -> int:
    """Convert a RouterOS rate component to bits per second."""
    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*([kKmMgG]?)\s*",
        value,
    )
    if not match:
        raise ValueError("Invalid RouterOS rate-limit component")

    amount, unit = match.groups()
    multiplier = {
        "": 1,
        "k": 1_000,
        "m": 1_000_000,
        "g": 1_000_000_000,
    }[unit.lower()]

    try:
        return int(Decimal(amount) * multiplier)
    except InvalidOperation as exc:
        raise ValueError("Invalid RouterOS rate-limit component") from exc


def _rate_limit_matches(
    actual: str,
    upload_speed_mbps: int,
    download_speed_mbps: int,
) -> bool:
    """Compare RouterOS upload/download limits with purchased Mbps speeds."""
    if not isinstance(actual, str):
        return False

    components = actual.split("/")
    if len(components) != 2:
        return False

    try:
        actual_upload = _rate_component_to_bps(components[0])
        actual_download = _rate_component_to_bps(components[1])
    except ValueError:
        return False

    return (
        actual_upload == upload_speed_mbps * 1_000_000
        and actual_download == download_speed_mbps * 1_000_000
    )


def activate_hotspot_device(
    mac_address: str,
    download_speed_mbps: int,
    upload_speed_mbps: int,
    ip_address: str | None = None,
) -> dict:
    """
    Authorize a device through MikroTik Hotspot MAC authentication.

    A device is reported ACTIVE only after RouterOS confirms its active
    Hotspot session, assigned speed profile, and per-device Simple Queue
    match the purchased package.
    """
    mac = _normalize_mac(mac_address)
    download_speed = _validate_speed(
        download_speed_mbps, "Download speed"
    )
    upload_speed = _validate_speed(
        upload_speed_mbps, "Upload speed"
    )

    settings = router_settings()
    expected_identity = settings.get("expected_identity")

    if not expected_identity:
        raise RouterActivationError(
            "Expected MikroTik router identity is not configured"
        )

    api = connect_router()

    try:
        # Confirm that we are connected to the intended router.
        identities = list(api.path("system", "identity"))

        if not identities or identities[0].get("name") != expected_identity:
            raise RouterActivationError(
                "Connected router identity does not match WEZA configuration"
            )

        # Find the configured WEZA Hotspot server.
        hotspot_servers = list(api.path("ip", "hotspot"))

        matching_servers = [
            server
            for server in hotspot_servers
            if server.get("interface") == HOTSPOT_INTERFACE
            and server.get("profile") == HOTSPOT_PROFILE
            and server.get("disabled") != "true"
        ]

        if len(matching_servers) != 1:
            raise RouterActivationError(
                "Expected exactly one enabled WEZA Hotspot server "
                f"on {HOTSPOT_INTERFACE} using {HOTSPOT_PROFILE}"
            )

        server_name = matching_servers[0].get("name")

        if not server_name:
            raise RouterActivationError(
                "WEZA Hotspot server has no identifiable server name"
            )

        # RouterOS rate-limit order is upload/download.
        rate_limit = f"{upload_speed}M/{download_speed}M"
        speed_profile_name = (
            f"WEZA-{upload_speed}M-{download_speed}M"
        )

        profile_path = api.path("ip", "hotspot", "user", "profile")
        profiles = list(profile_path)

        matching_profiles = [
            profile
            for profile in profiles
            if profile.get("name") == speed_profile_name
        ]

        if len(matching_profiles) > 1:
            raise RouterActivationError(
                "Duplicate WEZA speed profiles found on MikroTik"
            )

        if matching_profiles:
            speed_profile = matching_profiles[0]

            if speed_profile.get("rate-limit") != rate_limit:
                profile_path.update(
                    **{
                        ".id": speed_profile[".id"],
                        "rate-limit": rate_limit,
                    }
                )
        else:
            profile_path.add(
                name=speed_profile_name,
                **{"rate-limit": rate_limit},
            )

        # Create or update the Hotspot user identified by the device MAC.
        user_path = api.path("ip", "hotspot", "user")
        users = list(user_path)

        matching_users = [
            user
            for user in users
            if user.get("name", "").upper() == mac
        ]

        if len(matching_users) > 1:
            raise RouterActivationError(
                "Duplicate Hotspot users found for this device MAC"
            )

        if matching_users:
            hotspot_user = matching_users[0]

            user_path.update(
                **{
                    ".id": hotspot_user[".id"],
                    "profile": speed_profile_name,
                    "server": server_name,
                    "disabled": "no",
                }
            )
        else:
            user_path.add(
                name=mac,
                profile=speed_profile_name,
                server=server_name,
                disabled="no",
            )

        # Allow RouterOS time to authenticate the device through MAC login.
        authentication_deadline = time.monotonic() + 5
        matching_active_devices = []

        while time.monotonic() < authentication_deadline:
            active_devices = list(api.path("ip", "hotspot", "active"))

            matching_active_devices = [
                device
                for device in active_devices
                if device.get("user", "").upper() == mac
                and device.get("server") == server_name
            ]

            if ip_address:
                matching_active_devices = [
                    device
                    for device in matching_active_devices
                    if device.get("address") == ip_address
                ]

            if len(matching_active_devices) == 1:
                break

            time.sleep(0.25)

        if len(matching_active_devices) != 1:
            raise RouterActivationError(
                "Hotspot user was configured, but RouterOS did not "
                "confirm exactly one active session within 5 seconds"
            )

        # Verify the user is assigned the expected speed profile.
        verified_users = [
            user
            for user in list(user_path)
            if user.get("name", "").upper() == mac
        ]

        if len(verified_users) != 1:
            raise RouterActivationError(
                "Could not verify the device Hotspot user"
            )

        if verified_users[0].get("profile") != speed_profile_name:
            raise RouterActivationError(
                "Device Hotspot user has an unexpected speed profile"
            )

        verified_profiles = [
            profile
            for profile in list(profile_path)
            if profile.get("name") == speed_profile_name
        ]

        if (
            len(verified_profiles) != 1
            or verified_profiles[0].get("rate-limit") != rate_limit
        ):
            raise RouterActivationError(
                "Could not verify the purchased speed limit"
            )

        # Verify the dynamic per-device Simple Queue created by Hotspot.
        active_ip = matching_active_devices[0].get("address")

        if not active_ip:
            raise RouterActivationError(
                "Active Hotspot session has no IP address for queue verification"
            )

        try:
            parsed_ip = ipaddress.ip_address(active_ip)
        except ValueError as exc:
            raise RouterActivationError(
                "Active Hotspot session has an invalid IP address"
            ) from exc

        queue_path = api.path("queue", "simple")
        queues = list(queue_path)

        expected_queue_name = f"<hotspot-{mac}>"
        matching_queues = []

        for queue in queues:
            if queue.get("name") != expected_queue_name:
                continue

            targets = queue.get("target", "")
            if not isinstance(targets, str):
                continue

            for target in targets.split(","):
                try:
                    parsed_target = ipaddress.ip_interface(target.strip())
                except ValueError:
                    continue

                if (
                    parsed_target.ip == parsed_ip
                    and parsed_target.network.prefixlen == parsed_ip.max_prefixlen
                ):
                    matching_queues.append(queue)
                    break

        if len(matching_queues) != 1:
            raise RouterActivationError(
                "Could not verify exactly one per-device Hotspot speed queue"
            )

        if not _rate_limit_matches(
            matching_queues[0].get("max-limit"),
            upload_speed,
            download_speed,
        ):
            raise RouterActivationError(
                "Device Simple Queue does not enforce the purchased speed limit"
            )

        return {
            "status": "ACTIVE",
            "mac_address": mac,
            "ip_address": str(parsed_ip),
            "server": server_name,
            "profile": speed_profile_name,
            "download_speed_mbps": download_speed,
            "upload_speed_mbps": upload_speed,
            "rate_limit": rate_limit,
        }

    finally:
        api.close()
