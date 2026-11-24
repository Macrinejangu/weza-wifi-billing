"""Tests for decide_query_settlement: settling a payment from a status query.

Pure logic, no database. The callback rule is tested in test_settlement_plan.py.
"""

from itertools import product

import pytest

from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.payments.callback_verification import CallbackVerdict
from app.payments.settlement_plan import (
    SettlementAction,
    decide_query_settlement,
    decide_settlement,
)
from app.payments.statuses import PaymentStatus

PENDING = PaymentStatus.PENDING
EXPIRED = PaymentStatus.EXPIRED
SUCCESSFUL = PaymentStatus.SUCCESSFUL
FAILED = PaymentStatus.FAILED
PAID = StkQueryOutcome.PAID
QUERY_FAILED = StkQueryOutcome.FAILED
UNKNOWN = StkQueryOutcome.UNKNOWN

APPLY_SUCCESS = SettlementAction.APPLY_SUCCESS
APPLY_FAILURE = SettlementAction.APPLY_FAILURE
KEEP_PENDING = SettlementAction.KEEP_PENDING
ALREADY_SETTLED = SettlementAction.ALREADY_SETTLED
REJECT = SettlementAction.REJECT

OPEN = {PENDING, EXPIRED}

# The whole decision table: (stored status, query outcome) -> action.
EXPECTED = {
    (PENDING, PAID): APPLY_SUCCESS,
    (PENDING, QUERY_FAILED): APPLY_FAILURE,
    (PENDING, UNKNOWN): KEEP_PENDING,
    (EXPIRED, PAID): APPLY_SUCCESS,
    (EXPIRED, QUERY_FAILED): ALREADY_SETTLED,
    (EXPIRED, UNKNOWN): KEEP_PENDING,
    (SUCCESSFUL, PAID): ALREADY_SETTLED,
    (SUCCESSFUL, QUERY_FAILED): REJECT,
    (SUCCESSFUL, UNKNOWN): ALREADY_SETTLED,
    (FAILED, PAID): REJECT,
    (FAILED, QUERY_FAILED): ALREADY_SETTLED,
    (FAILED, UNKNOWN): ALREADY_SETTLED,
}


@pytest.mark.parametrize(("status", "outcome"), list(EXPECTED))
def test_decision_table_row(status, outcome):
    assert (
        decide_query_settlement(current_status=status, query_outcome=outcome)
        == EXPECTED[(status, outcome)]
    )


def test_table_covers_every_status_and_outcome_combination():
    every_combination = set(product(PaymentStatus, StkQueryOutcome))
    assert set(EXPECTED) == every_combination


def test_success_is_applied_only_to_an_open_payment_the_query_says_is_paid():
    for status, outcome in product(PaymentStatus, StkQueryOutcome):
        action = decide_query_settlement(current_status=status, query_outcome=outcome)
        assert (action == APPLY_SUCCESS) == (status in OPEN and outcome == PAID)


def test_failure_is_applied_only_to_a_pending_payment_the_query_says_failed():
    for status, outcome in product(PaymentStatus, StkQueryOutcome):
        action = decide_query_settlement(current_status=status, query_outcome=outcome)
        assert (action == APPLY_FAILURE) == (
            status == PENDING and outcome == QUERY_FAILED
        )


@pytest.mark.parametrize("status", list(PaymentStatus))
def test_an_unknown_answer_never_changes_the_payment(status):
    action = decide_query_settlement(current_status=status, query_outcome=UNKNOWN)
    assert action in (KEEP_PENDING, ALREADY_SETTLED)


def test_an_unrecognised_stored_status_is_rejected():
    for outcome in StkQueryOutcome:
        assert (
            decide_query_settlement(current_status="bogus", query_outcome=outcome)
            == REJECT
        )


# Cross-checks: where a callback and a query-only settle the same situation,
# the two rules must agree.
@pytest.mark.parametrize(
    ("status", "outcome", "verdict"),
    [
        (PENDING, PAID, CallbackVerdict.SUCCESS_MATCHED),
        (EXPIRED, PAID, CallbackVerdict.SUCCESS_MATCHED),
        (PENDING, QUERY_FAILED, CallbackVerdict.FAILURE_MATCHED),
        (EXPIRED, QUERY_FAILED, CallbackVerdict.FAILURE_MATCHED),
        (SUCCESSFUL, PAID, CallbackVerdict.SUCCESS_MATCHED),
        (FAILED, QUERY_FAILED, CallbackVerdict.FAILURE_MATCHED),
        (FAILED, PAID, CallbackVerdict.SUCCESS_MATCHED),
    ],
)
def test_query_rule_agrees_with_the_callback_rule(status, outcome, verdict):
    from_query = decide_query_settlement(current_status=status, query_outcome=outcome)
    from_callback = decide_settlement(
        verdict=verdict, current_status=status, query_outcome=outcome
    )
    assert from_query == from_callback
    