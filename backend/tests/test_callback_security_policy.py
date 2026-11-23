"""Tests for the combined callback gate (IP policy plus secret token)."""
import pytest

from app.payments.callback_ip_policy import CallbackIpPolicy
from app.payments.callback_security import (
    CallbackDecision,
    CallbackSecurityPolicy,
)

TOKEN = "abcdefghijklmnopqrstuvwxyz012345"  # 32 URL-safe characters
LISTED_IP = "196.201.214.200"
STRANGER_IP = "203.0.113.5"
PROXY = "127.0.0.1"


def make_policy(ip_enabled=True, trusted_proxies=()):
    ip_policy = CallbackIpPolicy.create(
        enabled=ip_enabled, trusted_proxies=trusted_proxies
    )
    return CallbackSecurityPolicy(ip_policy=ip_policy, token=TOKEN)


def check(policy, peer=LISTED_IP, token=TOKEN, forwarded_for=None):
    return policy.check(peer=peer, forwarded_for=forwarded_for, received_token=token)


def test_listed_address_and_correct_token_is_allowed():
    assert check(make_policy()) is CallbackDecision.ALLOWED


def test_stranger_address_with_the_correct_token_is_rejected_on_ip():
    assert check(make_policy(), peer=STRANGER_IP) is CallbackDecision.REJECTED_IP


@pytest.mark.parametrize(
    "wrong_token",
    ["", None, TOKEN[:-1], TOKEN.upper(), "x" * 32],
)
def test_listed_address_with_a_wrong_token_is_rejected_on_token(wrong_token):
    decision = check(make_policy(), token=wrong_token)

    assert decision is CallbackDecision.REJECTED_TOKEN


def test_ip_is_checked_before_the_token():
    # Both are wrong: the IP decision must win, always.
    decision = check(make_policy(), peer=STRANGER_IP, token="wrong")

    assert decision is CallbackDecision.REJECTED_IP


def test_disabled_ip_policy_still_requires_the_token():
    policy = make_policy(ip_enabled=False)

    assert check(policy, peer=STRANGER_IP, token="wrong") is CallbackDecision.REJECTED_TOKEN


def test_disabled_ip_policy_with_the_correct_token_is_allowed():
    policy = make_policy(ip_enabled=False)

    assert check(policy, peer=STRANGER_IP) is CallbackDecision.ALLOWED


def test_forwarded_address_from_a_trusted_proxy_is_used():
    policy = make_policy(trusted_proxies=[PROXY])

    decision = check(policy, peer=PROXY, forwarded_for=LISTED_IP)

    assert decision is CallbackDecision.ALLOWED


@pytest.mark.parametrize(
    "bad_token",
    ["", "short", None, "a" * 129, "a" * 32 + "\n"],
)
def test_weak_configured_token_refuses_to_start(bad_token):
    ip_policy = CallbackIpPolicy.create(enabled=True)

    with pytest.raises(ValueError):
        CallbackSecurityPolicy(ip_policy=ip_policy, token=bad_token)


def test_repr_does_not_contain_the_token():
    assert TOKEN not in repr(make_policy())


def test_decision_values_are_the_agreed_set():
    assert {d.value for d in CallbackDecision} == {
        "allowed",
        "rejected_ip",
        "rejected_token",
    }