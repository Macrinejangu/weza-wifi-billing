def activate_wifi_session(session_id: int) -> dict:
    """
    Simulate activating a customer's Wi-Fi access.
    """
    return {
        "session_id": session_id,
        "status": "ACTIVE",
        "message": "Wi-Fi access activated successfully"
    }


def disconnect_wifi_session(session_id: int) -> dict:
    """
    Simulate disconnecting a customer's Wi-Fi access.
    """
    return {
        "session_id": session_id,
        "status": "DISCONNECTED",
        "message": "Wi-Fi session disconnected successfully"
    }
