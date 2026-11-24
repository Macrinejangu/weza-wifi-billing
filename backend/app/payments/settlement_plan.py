"""Decide what a verified callback, or a status query alone, does to a payment.

This module is pure logic with no database or network access, so every
rule can be tested exhaustively. The callers are:

1. Phase 1 (no lock): ask requires_status_query(); if True, call the STK query.
2. Phase 2 (row locked): re-read the payment status, then ask decide_settlement().
3. Sweeper (no callback ever arrived): ask the STK query, then, with the row
   locked and the status re-read, ask decide_query_settlement().

Fail-closed rules:
* Callbacks are unsigned, so a callback alone never grants access. A payment
  becomes successful or failed only when the STK status query agrees.
* Contradictions (callback and query disagree) and unknown answers keep the
  payment pending. Pending never grants access.
* A failed payment is final. A late success for a failed payment is
  rejected and recorded for staff, not applied.
"""

from enum import StrEnum

from app.integrations.mpesa.stk_query import StkQueryOutcome
from app.payments.callback_verification import CallbackVerdict
from app.payments.statuses import PaymentStatus


class SettlementAction(StrEnum):
    """What phase 2 must do to the payment row."""

    APPLY_SUCCESS = "apply_success"
    APPLY_FAILURE = "apply_failure"
    KEEP_PENDING = "keep_pending"
    ALREADY_SETTLED = "already_settled"
    REJECT = "reject"


# Verdicts that mean "the callback matched our stored payment".
_MATCHED_VERDICTS = {
    CallbackVerdict.SUCCESS_MATCHED,
    CallbackVerdict.FAILURE_MATCHED,
}

# Statuses in which a payment can still change.
_OPEN_STATUSES = {PaymentStatus.PENDING, PaymentStatus.EXPIRED}


def requires_status_query(
    verdict: CallbackVerdict, current_status: PaymentStatus
) -> bool:
    """Return True only when the answer could change the payment.

    Saves a network call for rejected or already-settled callbacks.
    """
    return verdict in _MATCHED_VERDICTS and current_status in _OPEN_STATUSES


def decide_settlement(
    *,
    verdict: CallbackVerdict,
    current_status: PaymentStatus,
    query_outcome: StkQueryOutcome | None,
) -> SettlementAction:
    """Choose the single action for this callback.

    current_status must be the status read UNDER THE ROW LOCK, not the one
    read in phase 1, because another callback may have settled it meanwhile.
    """
    # 1. Anything that did not match our stored payment is rejected.
    if verdict not in _MATCHED_VERDICTS:
        return SettlementAction.REJECT

    # 2. Payment already settled: a repeat callback must change nothing.
    if current_status == PaymentStatus.SUCCESSFUL:
        return SettlementAction.ALREADY_SETTLED

    if current_status == PaymentStatus.FAILED:
        # Failed is final. A repeated failure is harmless; a success after
        # a failure is suspicious and is recorded for staff.
        if verdict == CallbackVerdict.FAILURE_MATCHED:
            return SettlementAction.ALREADY_SETTLED
        return SettlementAction.REJECT

    # 3. Open payment (pending, or expired awaiting a possible late success).
    if verdict == CallbackVerdict.FAILURE_MATCHED:
        if current_status == PaymentStatus.EXPIRED:
            return SettlementAction.ALREADY_SETTLED  # expired -> failed is not allowed
        if query_outcome == StkQueryOutcome.FAILED:
            return SettlementAction.APPLY_FAILURE
        return SettlementAction.KEEP_PENDING

    # verdict is SUCCESS_MATCHED from here on.
    if query_outcome == StkQueryOutcome.PAID:
        return SettlementAction.APPLY_SUCCESS
    return SettlementAction.KEEP_PENDING


def decide_query_settlement(
    *,
    current_status: PaymentStatus,
    query_outcome: StkQueryOutcome | None,
) -> SettlementAction:
    """Choose the single action when only a status query is available.

    Used by the sweeper, where no callback ever arrived. There is no verdict
    to check: the query was asked by our own checkout_request_id, so the only
    inputs are the status read UNDER THE ROW LOCK and the query outcome.

    Rules:
    * Open (pending or expired) and PAID: apply success.
    * Pending and FAILED: apply failure. Expired and FAILED: already settled,
      because expired -> failed is not allowed.
    * UNKNOWN (or no answer) never changes anything: an open payment stays
      pending, a settled payment is left as it is.
    * Successful then FAILED, and failed then PAID, contradict a final state
      and are rejected for staff.
    * An unrecognised stored status is rejected. Fail closed.
    """
    try:
        status = PaymentStatus(current_status)
    except ValueError:
        return SettlementAction.REJECT

    if status in _OPEN_STATUSES:
        if query_outcome == StkQueryOutcome.PAID:
            return SettlementAction.APPLY_SUCCESS
        if query_outcome == StkQueryOutcome.FAILED:
            if status == PaymentStatus.PENDING:
                return SettlementAction.APPLY_FAILURE
            return SettlementAction.ALREADY_SETTLED
        return SettlementAction.KEEP_PENDING

    if status == PaymentStatus.SUCCESSFUL:
        if query_outcome == StkQueryOutcome.FAILED:
            return SettlementAction.REJECT  # successful, then failed
        return SettlementAction.ALREADY_SETTLED

    # status is FAILED
    if query_outcome == StkQueryOutcome.PAID:
        return SettlementAction.REJECT  # failed, then paid
    return SettlementAction.ALREADY_SETTLED
