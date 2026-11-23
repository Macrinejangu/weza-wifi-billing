"""Tests for the callback IP allowlist."""
import ipaddress

import pytest

from app.payments.callback_ip_policy import (
    SAFARICOM_CALLBACK_IPS,
    CallbackIpPolicy,
    parse_ip,
)

ALLOWED_IP = "196.201.214.200"
PROXY = "127.0.0.1"


def enabled_policy(trusted_proxies=()):
    return CallbackIpPolicy.create(enabled=True, trusted_proxies=trusted_proxies)


def test_parse_ip_returns_an_address_object():
    assert parse_ip(ALLOWED_IP) == ipaddress.ip_address(ALLOWED_IP)


def test_parse_ip_unwraps_ipv4_mapped_ipv6():
    assert parse_ip("::ffff:196.201.214.200") == ipaddress.ip_address(ALLOWED_IP)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        5,
        "",
        "garbage",
        "196.201.214",
        "196.201.214.256",
        "196.201.214.200 ",
        "196.201.214.200\n",
        "196.201.214.0200",  # leading zero is ambiguous: rejected
        "١٩٦.٢٠١.٢١٤.٢٠٠",  # Arabic-Indic digits
        "196.201.214.200,196.201.214.206",
    ],
)
def test_parse_ip_rejects_everything_else(bad):
    assert parse_ip(bad) is None


def test_documented_safaricom_list_has_twelve_distinct_valid_addresses():
    assert len(SAFARICOM_CALLBACK_IPS) == 12
    assert len({parse_ip(ip) for ip in SAFARICOM_CALLBACK_IPS}) == 12
    assert None not in {parse_ip(ip) for ip in SAFARICOM_CALLBACK_IPS}


@pytest.mark.parametrize("peer", ["127.0.0.1", "garbage", None])
def test_disabled_policy_permits_everything(peer):
    policy = CallbackIpPolicy.create(enabled=False)

    assert policy.permits(peer) is True


@pytest.mark.parametrize("ip", SAFARICOM_CALLBACK_IPS)
def test_enabled_policy_permits_each_listed_address(ip):
    assert enabled_policy().permits(ip) is True


@pytest.mark.parametrize(
    "ip", ["203.0.113.5", "127.0.0.1", "::1", "196.201.214.201"]
)
def test_enabled_policy_rejects_other_addresses(ip):
    # 196.201.214.201 is one digit away from a listed address.
    assert enabled_policy().permits(ip) is False


@pytest.mark.parametrize("peer", [None, "", "garbage", 5])
def test_enabled_policy_rejects_an_unreadable_peer(peer):
    assert enabled_policy().permits(peer) is False


def test_ipv4_mapped_spelling_of_a_listed_address_is_permitted():
    assert enabled_policy().permits("::ffff:196.201.214.200") is True


def test_forwarded_header_is_ignored_when_the_peer_is_not_a_trusted_proxy():
    # A stranger forges the header to look like Safaricom.
    policy = enabled_policy(trusted_proxies=[PROXY])

    assert policy.permits("203.0.113.5", forwarded_for=ALLOWED_IP) is False


def test_trusted_proxy_forwarding_a_listed_address_is_permitted():
    policy = enabled_policy(trusted_proxies=[PROXY])

    assert policy.permits(PROXY, forwarded_for=ALLOWED_IP) is True


def test_trusted_proxy_forwarding_another_address_is_rejected():
    policy = enabled_policy(trusted_proxies=[PROXY])

    assert policy.permits(PROXY, forwarded_for="203.0.113.9") is False


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        # The client forged a listed address on the left; the real one is last.
        ("196.201.214.200, 203.0.113.9", False),
        ("203.0.113.9, 196.201.214.200", True),
        # Our own second proxy is skipped, then the real client is found.
        ("196.201.214.200, 10.0.0.2", True),
    ],
)
def test_the_rightmost_untrusted_hop_decides(header, expected):
    policy = enabled_policy(trusted_proxies=[PROXY, "10.0.0.2"])

    assert policy.permits(PROXY, forwarded_for=header) is expected


@pytest.mark.parametrize(
    "header",
    [
        "",
        "garbage",
        "196.201.214.200, garbage",
        5,
        "x" * 1001,
        "127.0.0.1",  # every hop is our own proxy: nothing proves the client
    ],
)
def test_unreadable_forwarded_header_from_a_trusted_proxy_is_rejected(header):
    policy = enabled_policy(trusted_proxies=[PROXY])

    assert policy.permits(PROXY, forwarded_for=header) is False


def test_trusted_proxy_without_a_header_falls_back_to_its_own_address():
    policy = enabled_policy(trusted_proxies=[PROXY])

    assert policy.permits(PROXY) is False


def test_enabled_policy_with_no_allowed_addresses_is_a_configuration_error():
    with pytest.raises(ValueError):
        CallbackIpPolicy.create(enabled=True, allowed=[])


@pytest.mark.parametrize(
    "kwargs",
    [{"allowed": ["garbage"]}, {"trusted_proxies": ["garbage"]}],
)
def test_create_rejects_an_invalid_address(kwargs):
    with pytest.raises(ValueError):
        CallbackIpPolicy.create(enabled=True, **kwargs)


def test_create_defaults_to_the_documented_safaricom_list():
    policy = CallbackIpPolicy.create(enabled=True)

    assert len(policy.allowed_ips) == 12
    assert policy.permits(ALLOWED_IP) is True