from sqlalchemy.orm import Session

from app.models import Package, Purchase, User


def create_purchase(db: Session, user_id: int, package_id: int, key: str):
    """Returns (purchase, created). The same idempotency key gives back the same purchase."""
    purchase = db.query(Purchase).filter_by(idempotency_key=key).first()
    if purchase:
        if (purchase.user_id, purchase.package_id) != (user_id, package_id):
            raise ValueError("Idempotency key already used for a different purchase")
        return purchase, False

    package = db.get(Package, package_id)
    if db.get(User, user_id) is None or package is None or not package.is_active:
        raise LookupError("User or active package not found")

    purchase = Purchase(  # copy price and package details so later edits don't change this sale
        user_id=user_id, package_id=package.id, amount=package.price, package_name=package.name,
        duration_minutes=package.duration_minutes, download_speed_mbps=package.download_speed_mbps,
        upload_speed_mbps=package.upload_speed_mbps, idempotency_key=key,
    )
    db.add(purchase)
    db.commit()
    return purchase, True
