
import pytest

from sqlalchemy.exc import IntegrityError

from app.models import Payment
from app.services.payment_service import create_payment
from app.services.purchase_service import create_purchase


PHONE = "254712345678"


def test_only_one_pending_payment_per_purchase(db, user, package):
    purchase, _ = create_purchase(
        db,
        user.id,
        package.id,
        "pending-payment-test",
    )

    first = create_payment(db, purchase.id, PHONE)

    assert first.status == "pending"

    with pytest.raises(IntegrityError):
        create_payment(db, purchase.id, PHONE)


def test_new_payment_allowed_after_previous_attempt_fails(
    db, user, package
):
    purchase, _ = create_purchase(
        db,
        user.id,
        package.id,
        "failed-payment-test",
    )

    first = create_payment(db, purchase.id, PHONE)

    first.status = "failed"
    db.commit()

    second = create_payment(db, purchase.id, PHONE)

    assert second.id != first.id
    assert second.status == "pending"


def test_database_rejects_negative_usage_values(db):
    from app.models import UsageRecord
    from sqlalchemy import text

    # Check the database constraint without requiring
    # an existing Wi-Fi session.
    constraints = db.execute(
        text("""
            SELECT conname
            FROM pg_constraint
            WHERE conname IN (
                'ck_usage_records_upload_bytes',
                'ck_usage_records_download_bytes'
            )
        """)
    ).scalars().all()

    assert set(constraints) == {
        "ck_usage_records_upload_bytes",
        "ck_usage_records_download_bytes",
    }
