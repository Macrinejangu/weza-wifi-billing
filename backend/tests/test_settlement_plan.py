"""Tests for the settlement decision table.

The decision table is pure logic, so these tests walk every combination of
verdict, payment status and status-query outcome. The most important test
is the invariant at the bottom: success may be applied only when all three
conditions (matched success callback, open payment, query says PAID) hold.
"""

from itertools import product

import pytest

from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.payments.callback_verification import CallbackVerdict
from app.payments.settlement_plan import (
    SettlementAction,
    decide_settlement,
    requires_status_query,
)
from app.payments.statuses import PaymentStatus

# None means "the status query was never made".
ALL_OUTCOMES = [*StkQueryOutcome, None]
ALL_STATUSES = list(PaymentStatus)
ALL_VERDICTS = list(CallbackVerdict)
OPEN_STATUSES = [PaymentStatus.PENDING, PaymentStatus.EXPIRED]
REJECTED_VERDICTS = [
    v
    for v in CallbackVerdict
    if v not in (CallbackVerdict.SUCCESS_MATCHED, CallbackVerdict.FAILURE_MATCHED)
]


def decide(verdict, status, outcome):
    """Call decide_settlement with keyword arguments, as production code does."""
    return decide_settlement(
        verdict=verdict, current_status=status, query_outcome=outcome
    )


@pytest.mark.parametrize(
    ("verdict", "status", "outcome"),
    list(product(REJECTED_VERDICTS, ALL_STATUSES, ALL_OUTCOMES)),
)
def test_unmatched_callbacks_are_always_rejected(verdict, status, outcome):
    # Even a query answer of PAID must not rescue a callback that failed
    # verification (wrong IDs, wrong amount, wrong phone, incomplete).
    assert decide(verdict, status, outcome) is SettlementAction.REJECT


def test_rejected_verdict_list_is_not_empty():
    # Guards the parametrized test above: an empty list would make it pass
    # without testing anything.
    assert len(REJECTED_VERDICTS) >= 1


@pytest.mark.parametrize("status", OPEN_STATUSES)
def test_matched_success_with_query_paid_applies_success(status):
    # Pending is the normal case; expired is a late success being repaired.
    assert (
        decide(CallbackVerdict.SUCCESS_MATCHED, status, StkQueryOutcome.PAID)
        is SettlementAction.APPLY_SUCCESS
    )


@pytest.mark.parametrize(
    ("status", "outcome"),
    list(
        product(
            OPEN_STATUSES,
            [StkQueryOutcome.FAILED, StkQueryOutcome.UNKNOWN, None],
        )
    ),
)
def test_matched_success_without_query_confirmation_stays_pending(status, outcome):
    # Fail closed: contradiction, unknown answer, or no query at all.
    assert (
        decide(CallbackVerdict.SUCCESS_MATCHED, status, outcome)
        is SettlementAction.KEEP_PENDING
    )


def test_matched_failure_confirmed_by_query_applies_failure():
    assert (
        decide(
            CallbackVerdict.FAILURE_MATCHED,
            PaymentStatus.PENDING,
            StkQueryOutcome.FAILED,
        )
        is SettlementAction.APPLY_FAILURE
    )


@pytest.mark.parametrize(
    "outcome", [StkQueryOutcome.PAID, StkQueryOutcome.UNKNOWN, None]
)
def test_forged_or_unconfirmed_failure_stays_pending(outcome):
    # A failure callback is unsigned, so it cannot cancel a payment alone.
    assert (
        decide(CallbackVerdict.FAILURE_MATCHED, PaymentStatus.PENDING, outcome)
        is SettlementAction.KEEP_PENDING
    )


@pytest.mark.parametrize("outcome", ALL_OUTCOMES)
def test_failure_callback_for_expired_payment_changes_nothing(outcome):
    # expired -> failed is not an allowed transition in statuses.py.
    assert (
        decide(CallbackVerdict.FAILURE_MATCHED, PaymentStatus.EXPIRED, outcome)
        is SettlementAction.ALREADY_SETTLED
    )


@pytest.mark.parametrize(
    ("verdict", "outcome"),
    list(
        product(
            [CallbackVerdict.SUCCESS_MATCHED, CallbackVerdict.FAILURE_MATCHED],
            ALL_OUTCOMES,
        )
    ),
)
def test_repeat_callback_for_successful_payment_changes_nothing(verdict, outcome):
    # Duplicate-callback safety: the second delivery must be a no-op.
    assert (
        decide(verdict, PaymentStatus.SUCCESSFUL, outcome)
        is SettlementAction.ALREADY_SETTLED
    )


@pytest.mark.parametrize("outcome", ALL_OUTCOMES)
def test_repeat_failure_for_failed_payment_changes_nothing(outcome):
    assert (
        decide(CallbackVerdict.FAILURE_MATCHED, PaymentStatus.FAILED, outcome)
        is SettlementAction.ALREADY_SETTLED
    )


@pytest.mark.parametrize("outcome", ALL_OUTCOMES)
def test_success_after_failure_is_rejected_even_if_query_says_paid(outcome):
    # Failed is final. A contradiction is recorded for staff, not applied.
    assert (
        decide(CallbackVerdict.SUCCESS_MATCHED, PaymentStatus.FAILED, outcome)
        is SettlementAction.REJECT
    )


@pytest.mark.parametrize(
    ("verdict", "status"),
    list(product(ALL_VERDICTS, ALL_STATUSES)),
)
def test_query_is_only_needed_for_matched_callbacks_on_open_payments(verdict, status):
    matched = verdict in (
        CallbackVerdict.SUCCESS_MATCHED,
        CallbackVerdict.FAILURE_MATCHED,
    )
    expected = matched and status in OPEN_STATUSES
    assert requires_status_query(verdict, status) is expected


@pytest.mark.parametrize(
    ("verdict", "status", "outcome"),
    list(product(ALL_VERDICTS, ALL_STATUSES, ALL_OUTCOMES)),
)
def test_success_is_applied_only_when_every_condition_holds(verdict, status, outcome):
    """The safety invariant for the whole table.

    APPLY_SUCCESS (the only action that leads to internet access) must
    happen if and only if: the callback matched as a success, the payment is
    still open, and the status query itself said PAID.
    """
    action = decide(verdict, status, outcome)
    all_conditions_hold = (
        verdict is CallbackVerdict.SUCCESS_MATCHED
        and status in OPEN_STATUSES
        and outcome is StkQueryOutcome.PAID
    )
    assert (action is SettlementAction.APPLY_SUCCESS) is all_conditions_hold


@pytest.mark.parametrize(
    ("verdict", "status", "outcome"),
    list(product(ALL_VERDICTS, ALL_STATUSES, ALL_OUTCOMES)),
)
def test_failure_is_applied_only_for_confirmed_failure_on_pending(
    verdict, status, outcome
):
    action = decide(verdict, status, outcome)
    all_conditions_hold = (
        verdict is CallbackVerdict.FAILURE_MATCHED
        and status is PaymentStatus.PENDING
        and outcome is StkQueryOutcome.FAILED
    )
    assert (action is SettlementAction.APPLY_FAILURE) is all_conditions_hold