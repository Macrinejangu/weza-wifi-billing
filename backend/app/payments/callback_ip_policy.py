"""IP allowlist for Daraja callbacks.

Daraja asks merchants to accept callbacks only from the Safaricom API gateway
addresses listed in its documentation. This is a cheap first gate: it turns
strangers away before we read a body or touch the database. It is NOT proof
of anything on its own, because addresses can be spoofed in some network
setups. A payload must still match a payment we created and success is still
confirmed with the STK status query.

Behaviour:
  * DISABLED policy allows every request. This is for local sandbox work
    behind a tunnel, where the visible address is the tunnel's. Whether the
    sandbox sends from the listed addresses is UNVERIFIED, so production
    enablement waits for a sandbox experiment.
  * ENABLED policy allows only listed addresses. Anything unreadable is
    rejected (fail closed).
  * X-Forwarded-For is trusted ONLY when the direct peer is a configured
    trusted proxy, because anyone can send that header themselves.
"""
import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

# From the Daraja portal (Callback and IP Whitelisting). Re-check the portal
# before go-live: an outdated list would silently reject genuine callbacks.
SAFARICOM_CALLBACK_IPS: tuple[str, ...] = (
    "196.201.214.200",
    "196.201.214.206",
    "196.201.213.114",
    "196.201.214.207",
    "196.201.214.208",
    "196.201.213.44",
    "196.201.212.127",
    "196.201.212.138",
    "196.201.212.129",
    "196.201.212.136",
    "196.201.212.74",
    "196.201.212.69",
)

# A real chain has a handful of hops; this stops absurd headers being parsed.
_MAX_FORWARDED_LENGTH = 1000


def parse_ip(value: object) -> IPAddress | None:
    """Return an IP address object, or None if `value` is not a clean address.

    IPv4-mapped IPv6 addresses are unwrapped to plain IPv4 so one address
    cannot appear in two spellings.
    """
    if not isinstance(value, str):
        return None
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _parse_all(values: Iterable[str], what: str) -> frozenset[IPAddress]:
    """Parse a list of configured addresses, or raise ValueError."""
    parsed = set()
    for value in values:
        address = parse_ip(value)
        if address is None:
            raise ValueError(f"{what} contains an invalid IP address")
        parsed.add(address)
    return frozenset(parsed)


@dataclass(frozen=True)
class CallbackIpPolicy:
    """Decides whether a request's address may reach the callback endpoint."""

    enabled: bool
    allowed_ips: frozenset[IPAddress]
    trusted_proxies: frozenset[IPAddress]

    def __post_init__(self) -> None:
        # An enabled policy with nothing allowed would reject every genuine
        # callback. That is a configuration mistake: fail loudly at startup.
        if self.enabled and not self.allowed_ips:
            raise ValueError("an enabled IP policy needs at least one allowed address")

    @classmethod
    def create(
        cls,
        *,
        enabled: bool,
        allowed: Iterable[str] = SAFARICOM_CALLBACK_IPS,
        trusted_proxies: Iterable[str] = (),
    ) -> "CallbackIpPolicy":
        """Build a policy from configured strings. Raises ValueError if bad."""
        return cls(
            enabled=enabled,
            allowed_ips=_parse_all(allowed, "allowed"),
            trusted_proxies=_parse_all(trusted_proxies, "trusted_proxies"),
        )

    def client_ip(self, peer: object, forwarded_for: object = None) -> IPAddress | None:
        """Work out the real client address, or None if it cannot be proven."""
        direct = parse_ip(peer)
        if direct is None:
            return None
        # The header is only believable when a proxy WE trust sent the request.
        if direct not in self.trusted_proxies or forwarded_for is None:
            return direct
        if not isinstance(forwarded_for, str) or len(forwarded_for) > _MAX_FORWARDED_LENGTH:
            return None
        # Each proxy appends the address it saw, so walk from the right and
        # skip our own proxies. The first other address is the real client.
        # Anything a client forged sits further left and is never reached.
        for hop in reversed([part.strip() for part in forwarded_for.split(",")]):
            address = parse_ip(hop)
            if address is None:
                return None
            if address not in self.trusted_proxies:
                return address
        return None

    def permits(self, peer: object, forwarded_for: object = None) -> bool:
        """True if the request may proceed."""
        if not self.enabled:
            return True
        address = self.client_ip(peer, forwarded_for)
        return address is not None and address in self.allowed_ips