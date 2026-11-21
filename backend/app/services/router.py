
import ssl

from librouteros import connect

from app.config import router_settings


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
