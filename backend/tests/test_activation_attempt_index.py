"""The database allows only one in-flight activation attempt per session (WEZA-51)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ActivationAttempt, WiFiSession

from test_payment_settlement import make_payment, make_purchase


@pytest.fixture
def session_row(db, user, package):
    purchase = make_purchase(db, user, package)
    payment = make_payment(db, purchase, status="successful", receipt="IDXTEST001")
    row = WiFiSession(
        user_id=user.id,
        package_id=package.id,
        payment_id=payment.id,
        status="PAYMENT_CONFIRMED",
    )
    db.add(row)
    db.commit()
    return row


def attempt(session_id, number, status):
    return ActivationAttempt(session_id=session_id, attempt_number=number, status=status)


def test_second_started_attempt_for_a_session_is_rejected(db, session_row):
    db.add(attempt(session_row.id, 1, "started"))
    db.commit()

    with pytest.raises(IntegrityError):
        db.add(attempt(session_row.id, 2, "started"))
        db.flush()
    db.rollback()


def test_new_attempt_is_allowed_after_the_previous_one_finished(db, session_row):
    db.add(attempt(session_row.id, 1, "failed"))
    db.add(attempt(session_row.id, 2, "started"))
    db.commit()

    assert db.query(ActivationAttempt).filter_by(session_id=session_row.id).count() == 2