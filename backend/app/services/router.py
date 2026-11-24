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

    rollback_state = {
        "user_snapshot": None,
        "user_id": None,
        "profile_snapshot": None,
        "profile_id": None,
        "profile_name": None,
        "new_session_ids": [],
        "unidentified_new_session": False,
        # RouterOS may complete authentication after our polling deadline.
        # Until a session is observed and identified, cleanup is unsafe.
        "authentication_outcome_uncertain": False,
        "unidentified_new_profile": False,
        "unidentified_new_user": False,
    }

    def rollback_router_changes():
        errors = []
        authentication_outcome_uncertain = rollback_state[
            "authentication_outcome_uncertain"
        ]
        session_rollback_failed = (
            rollback_state["unidentified_new_session"]
            or authentication_outcome_uncertain
        )

        if rollback_state["unidentified_new_session"]:
            errors.append(
                "A newly created Hotspot session has no RouterOS ID; "
                "it could not be safely removed"
            )

        if authentication_outcome_uncertain:
            errors.append(
                "Hotspot authentication was attempted but not confirmed; "
                "user configuration and the new speed profile were preserved "
                "because RouterOS may complete authentication after the timeout"
            )

        if rollback_state["new_session_ids"]:
            try:
                active_path = api.path("ip", "hotspot", "active")
            except Exception as exc:
                active_path = None
                session_rollback_failed = True
                errors.append(
                    f"Could not access active Hotspot sessions during rollback: {exc}"
                )

            if active_path is not None:
                for session_id in rollback_state["new_session_ids"]:
                    try:
                        active_path.remove(session_id)
                    except Exception as exc:
                        session_rollback_failed = True
                        errors.append(
                            f"New Hotspot session rollback failed "
                            f"for {session_id}: {exc}"
                        )

                try:
                    remaining_session_ids = {
                        session.get(".id")
                        for session in list(active_path)
                    }
                    remaining = [
                        session_id
                        for session_id in rollback_state["new_session_ids"]
                        if session_id in remaining_session_ids
                    ]

                    if remaining:
                        session_rollback_failed = True
                        errors.append(
                            "New Hotspot session(s) still exist after "
                            "rollback removal: "
                            + ", ".join(remaining)
                        )
                except Exception as exc:
                    session_rollback_failed = True
                    errors.append(
                        f"Could not verify Hotspot session removal: {exc}"
                    )

        # Check for replacement sessions using a different RouterOS ID.
        if rollback_state["new_session_ids"] and not session_rollback_failed:
            try:
                remaining_matching_sessions = [
                    session
                    for session in list(
                        api.path("ip", "hotspot", "active")
                    )
                    if session.get("user", "").upper() == mac
                    and session.get("server") == server_name
                ]

                if remaining_matching_sessions:
                    session_rollback_failed = True
                    errors.append(
                        "A matching Hotspot session remains active after "
                        "rollback; user configuration was preserved"
                    )

            except Exception as exc:
                session_rollback_failed = True
                errors.append(
                    "Could not verify that all matching Hotspot sessions "
                    f"were removed: {exc}"
                )

        if rollback_state["unidentified_new_user"]:
            errors.append(
                "A newly created Hotspot user has no RouterOS ID; "
                "it was preserved because it could not be safely removed"
            )

        if session_rollback_failed:
            errors.append(
                "Hotspot user configuration was preserved because "
                "session cleanup could not be confirmed"
            )
        elif not rollback_state["unidentified_new_user"]:
            try:
                user_path = api.path("ip", "hotspot", "user")
                snapshot = rollback_state["user_snapshot"]

                if snapshot is not None:
                    user_id = snapshot.get(".id")
                    if not user_id:
                        raise RuntimeError(
                            "Existing Hotspot user has no RouterOS ID"
                        )

                    restore = {
                        ".id": user_id,
                        **{
                            key: snapshot[key]
                            for key in ("profile", "server", "disabled")
                            if key in snapshot
                        },
                    }
                    user_path.update(**restore)

                elif rollback_state["user_id"]:
                    user_path.remove(rollback_state["user_id"])

            except Exception as exc:
                errors.append(f"Hotspot user rollback failed: {exc}")

        try:
            profile_path = api.path(
                "ip", "hotspot", "user", "profile"
            )
            snapshot = rollback_state["profile_snapshot"]

            if rollback_state["unidentified_new_profile"]:
                errors.append(
                    "A newly created speed profile has no RouterOS ID; "
                    "it was preserved because it could not be safely removed"
                )

            if rollback_state["profile_id"]:
                profile_name = rollback_state["profile_name"]

                # Preserve the profile if a session or unidentified user
                # may still depend on it.
                profile_in_use = (
                    session_rollback_failed
                    or rollback_state["unidentified_new_user"]
                )

                if not profile_in_use:
                    current_users = list(
                        api.path("ip", "hotspot", "user")
                    )

                    profile_in_use = any(
                        user.get("profile") == profile_name
                        for user in current_users
                    )

                if not profile_in_use:
                    current_users = list(
                        api.path("ip", "hotspot", "user")
                    )
                    users_by_name = {
                        user.get("name", "").upper(): user
                        for user in current_users
                        if user.get("name")
                    }
                    active_sessions = list(
                        api.path("ip", "hotspot", "active")
                    )

                    for session in active_sessions:
                        username = session.get("user", "").upper()
                        session_user = users_by_name.get(username)

                        # An unmatchable session makes profile usage
                        # uncertain, so do not delete the profile.
                        if session_user is None:
                            profile_in_use = True
                            break

                        if session_user.get("profile") == profile_name:
                            profile_in_use = True
                            break

                if not profile_in_use:
                    profile_path.remove(rollback_state["profile_id"])

        except Exception as exc:
            errors.append(f"Speed profile rollback failed: {exc}")

        return errors

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

        # Capture existing sessions before modifying the Hotspot user.
        active_path = api.path("ip", "hotspot", "active")
        preexisting_sessions = [
            device for device in list(active_path)
            if device.get("user", "").upper() == mac
            and device.get("server") == server_name
        ]

        if len(preexisting_sessions) > 1:
            raise RouterActivationError(
                "Multiple active sessions found for this device"
            )

        preexisting_session_ids = set()
        for device in preexisting_sessions:
            session_id = device.get(".id")
            if not session_id:
                raise RouterActivationError(
                    "Cannot safely reauthenticate without a RouterOS session ID"
                )
            preexisting_session_ids.add(session_id)

        # RouterOS rate-limit order is upload/download.
        rate_limit = f"{upload_speed}M/{download_speed}M"
        speed_profile_name = (
            f"WEZA-{upload_speed}M-{download_speed}M"
        )
        rollback_state["profile_name"] = speed_profile_name

        profile_path = api.path("ip", "hotspot", "user", "profile")
        profiles = list(profile_path)

        matching_profiles = [
            profile for profile in profiles
            if profile.get("name") == speed_profile_name
        ]

        if len(matching_profiles) > 1:
            raise RouterActivationError(
                "Duplicate WEZA speed profiles found on MikroTik"
            )

        user_path = api.path("ip", "hotspot", "user")
        users = list(user_path)
        matching_users = [
            user for user in users
            if user.get("name", "").upper() == mac
        ]

        if len(matching_users) > 1:
            raise RouterActivationError(
                "Duplicate Hotspot users found for this device MAC"
            )

        if preexisting_sessions:
            # Idempotent retry: verify existing resources without modifying them.
            if len(matching_profiles) != 1:
                raise RouterActivationError(
                    "Active device has no unique matching WEZA speed profile"
                )

            speed_profile = matching_profiles[0]
            if speed_profile.get("rate-limit") != rate_limit:
                raise RouterActivationError(
                    "Active device speed profile does not match the package"
                )

            if len(matching_users) != 1:
                raise RouterActivationError(
                    "Active device has no unique Hotspot user"
                )

            hotspot_user = matching_users[0]
            if (
                hotspot_user.get("profile") != speed_profile_name
                or hotspot_user.get("server") != server_name
                or hotspot_user.get("disabled") == "true"
            ):
                raise RouterActivationError(
                    "Active device Hotspot user does not match the package"
                )

            existing_ip = preexisting_sessions[0].get("address")
            if not existing_ip:
                raise RouterActivationError(
                    "Existing active session has no IP address"
                )

            if ip_address:
                try:
                    expected_ip = ipaddress.ip_address(ip_address)
                    actual_ip = ipaddress.ip_address(existing_ip)
                except ValueError as exc:
                    raise RouterActivationError(
                        "Invalid IP address supplied for active device"
                    ) from exc

                if actual_ip != expected_ip:
                    raise RouterActivationError(
                        "Existing active session IP does not match the device"
                    )

            matching_active_devices = preexisting_sessions

        else:
            # Only a device without an active session can enter this path.
            if matching_profiles:
                speed_profile = matching_profiles[0]
                if speed_profile.get("rate-limit") != rate_limit:
                    raise RouterActivationError(
                        "Existing speed profile rate limit does not match "
                        "the purchased package; existing profiles are immutable"
                    )
            else:
                rollback_state["profile_id"] = profile_path.add(
                    name=speed_profile_name,
                    **{"rate-limit": rate_limit},
                )
                if not rollback_state["profile_id"]:
                    rollback_state["unidentified_new_profile"] = True
                    raise RouterActivationError(
                        "Could not identify the newly created speed profile"
                    )

            if matching_users:
                hotspot_user = matching_users[0]
                rollback_state["user_snapshot"] = dict(hotspot_user)

                # Updating/enabling this user can trigger authentication
                # immediately. Keep rollback conservative until RouterOS
                # exposes a trackable active session.
                rollback_state["authentication_outcome_uncertain"] = True
                user_path.update(
                    **{
                        ".id": hotspot_user[".id"],
                        "profile": speed_profile_name,
                        "server": server_name,
                        "disabled": "no",
                    }
                )
            else:
                # A new user can authenticate as soon as it is created.
                rollback_state["authentication_outcome_uncertain"] = True
                rollback_state["user_id"] = user_path.add(
                    name=mac,
                    profile=speed_profile_name,
                    server=server_name,
                    disabled="no",
                )
                if not rollback_state["user_id"]:
                    rollback_state["unidentified_new_user"] = True
                    raise RouterActivationError(
                        "Could not identify the newly created Hotspot user"
                    )

            # Wait for RouterOS to authenticate the device.
            authentication_deadline = time.monotonic() + 5
            matching_active_devices = []

            while time.monotonic() < authentication_deadline:
                active_devices = list(active_path)

                matching_active_devices = [
                    device for device in active_devices
                    if device.get("user", "").upper() == mac
                    and device.get("server") == server_name
                ]

                # Record every newly created session before IP filtering
                # or session-count validation, so rollback can remove it.
                all_matching_sessions_identified = bool(
                    matching_active_devices
                )
                for device in matching_active_devices:
                    session_id = device.get(".id")

                    if not session_id:
                        all_matching_sessions_identified = False
                        if not preexisting_session_ids:
                            rollback_state["unidentified_new_session"] = True
                        continue

                    if (
                        session_id not in preexisting_session_ids
                        and session_id not in rollback_state["new_session_ids"]
                    ):
                        rollback_state["new_session_ids"].append(session_id)

                if all_matching_sessions_identified:
                    rollback_state["authentication_outcome_uncertain"] = False

                if len(matching_active_devices) > 1:
                    raise RouterActivationError(
                        "RouterOS confirmed multiple active Hotspot sessions "
                        "for this device"
                    )

                if len(matching_active_devices) == 1:
                    if (
                        ip_address
                        and matching_active_devices[0].get("address")
                        != ip_address
                    ):
                        raise RouterActivationError(
                            "Authenticated Hotspot session IP does not "
                            "match the device"
                        )
                    break

                time.sleep(0.25)

            if len(matching_active_devices) != 1:
                raise RouterActivationError(
                    "Hotspot user was configured, but RouterOS did not "
                    "confirm exactly one active session within 5 seconds"
                )

            if not matching_active_devices[0].get(".id"):
                raise RouterActivationError(
                    "Authenticated Hotspot session has no RouterOS ID"
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
            "router_identity": expected_identity,
            "router_session_id": matching_active_devices[0].get(".id"),
            "router_server_name": server_name,
        }

    except Exception as activation_error:
        rollback_errors = rollback_router_changes()

        if rollback_errors:
            raise RouterActivationError(
                f"Activation failed: {activation_error}. "
                f"Rollback also failed: {'; '.join(rollback_errors)}"
            ) from activation_error

        raise

    finally:
        api.close()


def disconnect_hotspot_device(
    mac_address: str,
    server_name: str,
    router_identity: str | None = None,
    router_session_id: str | None = None,
) -> dict:
    """
    Disable one WEZA Hotspot user and remove only its recorded active session.

    The recorded RouterOS session ID is checked before any router mutation.
    Disabling the user first prevents MAC authentication from immediately
    creating a replacement session after the active session is removed.
    """
    mac = _normalize_mac(mac_address)

    settings = router_settings()
    expected_identity = settings.get("expected_identity")

    if not expected_identity:
        raise RouterActivationError(
            "Expected MikroTik router identity is not configured"
        )

    if router_identity != expected_identity:
        raise RouterActivationError(
            "Recorded session router identity does not match "
            "the configured WEZA router"
        )

    if not server_name:
        raise RouterActivationError(
            "A verified WEZA Hotspot server name is required"
        )

    if not router_session_id:
        raise RouterActivationError(
            "Recorded RouterOS session ID is required for safe disconnection"
        )

    api = connect_router()

    try:
        identities = list(api.path("system", "identity"))

        if (
            not identities
            or identities[0].get("name") != expected_identity
        ):
            raise RouterActivationError(
                "Connected router identity does not match WEZA configuration"
            )

        hotspot_servers = list(api.path("ip", "hotspot"))

        matching_servers = [
            server
            for server in hotspot_servers
            if server.get("interface") == HOTSPOT_INTERFACE
            and server.get("profile") == HOTSPOT_PROFILE
            and server.get("disabled") != "true"
            and server.get("name") == server_name
        ]

        if len(matching_servers) != 1:
            raise RouterActivationError(
                "The recorded WEZA Hotspot server could not be verified"
            )

        users_path = api.path("ip", "hotspot", "user")

        def find_matching_users():
            return [
                user
                for user in list(users_path)
                if user.get("name", "").upper() == mac
                and user.get("server") == server_name
            ]

        matching_users = find_matching_users()

        if len(matching_users) != 1:
            raise RouterActivationError(
                "Expected exactly one matching WEZA Hotspot user; "
                "refusing ambiguous or unsafe disconnection"
            )

        hotspot_user = matching_users[0]
        user_id = hotspot_user.get(".id")

        if not user_id:
            raise RouterActivationError(
                "Matching Hotspot user has no identifiable RouterOS ID"
            )

        def is_disabled(user):
            return str(user.get("disabled", "false")).lower() in {
                "yes",
                "true",
            }

        active_path = api.path("ip", "hotspot", "active")

        def find_matching_sessions():
            return [
                device
                for device in list(active_path)
                if device.get("user", "").upper() == mac
                and device.get("server") == server_name
            ]

        # Verify the exact active session before changing router state.
        matches = find_matching_sessions()

        if len(matches) > 1:
            raise RouterActivationError(
                "Multiple active Hotspot sessions found; "
                "refusing ambiguous disconnection"
            )

        current_session_id = None

        if matches:
            current_session_id = matches[0].get(".id")

            if not current_session_id:
                raise RouterActivationError(
                    "Current RouterOS session has no identifiable ID"
                )

            if current_session_id != router_session_id:
                raise RouterActivationError(
                    "Active RouterOS session ID does not match the "
                    "recorded WEZA session; refusing disconnection"
                )

        # Disable MAC authentication only after exact-session verification.
        if not is_disabled(hotspot_user):
            users_path.update(
                **{
                    ".id": user_id,
                    "disabled": "yes",
                }
            )

        verified_users = find_matching_users()

        if len(verified_users) != 1 or not is_disabled(verified_users[0]):
            raise RouterActivationError(
                "RouterOS did not confirm that the Hotspot user was disabled"
            )

        # An absent session is safe to treat as an idempotent retry.
        if current_session_id is not None:
            active_path.remove(current_session_id)

        remaining_matches = find_matching_sessions()

        if remaining_matches:
            raise RouterActivationError(
                "RouterOS did not confirm that the recorded Hotspot session "
                "was disconnected"
            )

        final_users = find_matching_users()

        if len(final_users) != 1 or not is_disabled(final_users[0]):
            raise RouterActivationError(
                "Hotspot user is not confirmed disabled after disconnection"
            )

        return {
            "status": "DISCONNECTED",
            "mac_address": mac,
            "server": server_name,
            "router_identity": expected_identity,
            "router_session_id": router_session_id,
            "already_disconnected": current_session_id is None,
            "user_disabled": True,
        }

    finally:
        api.close()
