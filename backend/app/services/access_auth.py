import os
from typing import Protocol
from dotenv import load_dotenv
from app.config import ROOT_ENV
from app.services.router import (
    activate_hotspot_device,
    disconnect_hotspot_device,
)
from app.services.mock_router import disconnect_wifi_session


class AccessAuthenticator(Protocol):
    """Interface for interchangeable customer access providers."""

    def activate_device(
        self,
        mac_address: str | None,
        ip_address: str | None,
        download_speed_mbps: int,
        upload_speed_mbps: int,
    ) -> dict:
        ...

    def disconnect_device(
        self,
        session_id: int,
        mac_address: str | None,
        server_name: str | None,
        router_identity: str | None,
        router_session_id: str | None,
    ) -> dict:
        ...


class MockAuthenticator:
    """Development provider that simulates successful access activation."""

    def activate_device(
        self,
        mac_address: str | None,
        ip_address: str | None,
        download_speed_mbps: int,
        upload_speed_mbps: int,
    ) -> dict:
        return {
            "status": "ACTIVE",
            "mac_address": mac_address,
            "ip_address": ip_address,
            "download_speed_mbps": download_speed_mbps,
            "upload_speed_mbps": upload_speed_mbps,
            "message": "Mock Wi-Fi access activated successfully",
        }

    def disconnect_device(
        self,
        session_id: int,
        mac_address: str | None,
        server_name: str | None,
        router_identity: str | None,
        router_session_id: str | None,
    ) -> dict:
        result = disconnect_wifi_session(session_id)
        return {
            **result,
            "status": result.get("status"),
            "mac_address": mac_address,
            "server": server_name,
        }


class MikroTikAuthenticator:
    """Direct MikroTik Hotspot authentication provider."""

    def activate_device(
        self,
        mac_address: str | None,
        ip_address: str | None,
        download_speed_mbps: int,
        upload_speed_mbps: int,
    ) -> dict:
        if not mac_address:
            raise ValueError(
                "A device MAC address is required for MikroTik activation"
            )

        return activate_hotspot_device(
            mac_address=mac_address,
            ip_address=ip_address,
            download_speed_mbps=download_speed_mbps,
            upload_speed_mbps=upload_speed_mbps,
        )

    def disconnect_device(
        self,
        session_id: int,
        mac_address: str | None,
        server_name: str | None,
        router_identity: str | None,
        router_session_id: str | None,
    ) -> dict:
        if not mac_address:
            raise ValueError(
                "A device MAC address is required for MikroTik disconnection"
            )

        if not server_name:
            raise ValueError(
                "A Hotspot server name is required for MikroTik disconnection"
            )

        if not router_identity:
            raise ValueError(
                "Recorded router identity is required for MikroTik disconnection"
            )

        return disconnect_hotspot_device(
            mac_address=mac_address,
            server_name=server_name,
            router_identity=router_identity,
            router_session_id=router_session_id,
        )


def get_access_authenticator() -> AccessAuthenticator:
    load_dotenv(ROOT_ENV)

    mode = os.getenv("ROUTER_MODE", "").strip().lower()

    if mode == "mock":
        return MockAuthenticator()

    if mode == "mikrotik":
        return MikroTikAuthenticator()

    raise RuntimeError(
        "ROUTER_MODE must explicitly be either 'mock' or 'mikrotik'."
    )


def activate_access_device(
    mac_address: str | None,
    ip_address: str | None,
    download_speed_mbps: int,
    upload_speed_mbps: int,
) -> dict:
    """Activate access through the configured authentication provider."""
    authenticator = get_access_authenticator()

    return authenticator.activate_device(
        mac_address=mac_address,
        ip_address=ip_address,
        download_speed_mbps=download_speed_mbps,
        upload_speed_mbps=upload_speed_mbps,
    )


def disconnect_access_device(
    session_id: int,
    mac_address: str | None,
    server_name: str | None,
    router_identity: str | None,
    router_session_id: str | None,
) -> dict:
    """Disconnect access through the configured authentication provider."""
    authenticator = get_access_authenticator()

    return authenticator.disconnect_device(
        session_id=session_id,
        mac_address=mac_address,
        server_name=server_name,
        router_identity=router_identity,
        router_session_id=router_session_id,
    )
