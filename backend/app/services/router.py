from librouteros import connect

from app.config import router_settings


def connect_router():
    settings = router_settings()

    return connect(
        host=settings["host"],
        username=settings["username"],
        password=settings["password"],
        port=settings["port"],
        timeout=settings["timeout"],
    )


def get_router_identity() -> dict:
    api = connect_router()

    try:
        identity = list(api.path("system", "identity"))
        return identity[0] if identity else {}
    finally:
        api.close()
