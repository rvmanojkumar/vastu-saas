from sqlalchemy.orm import Session
from datetime import datetime

from app.models.subscription import Subscription


VALID_PRODUCTS = {"vastu", "numerology"}


def get_active_subscription(db: Session, user_id: int):
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
        .order_by(Subscription.id.desc())
        .first()
    )


def check_subscription(db: Session, user_id: int, product: str = "vastu"):
    """
    Validates user subscription for report generation.
    `product` is accepted for API compatibility (vastu | numerology).
    """
    if product not in VALID_PRODUCTS:
        return False, f"Invalid product: {product}"

    sub = get_active_subscription(db, user_id)

    if not sub:
        return False, "No active subscription found"

    if sub.status != "active":
        return False, "Subscription is not active"

    if sub.end_date and sub.end_date < datetime.utcnow():
        return False, "Subscription expired"

    # Optional product_access gate when the column exists / is populated
    access = (getattr(sub, "product_access", None) or "both").lower()
    if access not in ("both", product):
        return False, f"Your plan does not include {product} reports"

    limit = sub.reports_limit or 0
    used = sub.reports_used or 0

    # Prefer per-product counters when present and configured
    if product == "numerology":
        product_limit = getattr(sub, "numerology_reports_limit", None)
        product_used = getattr(sub, "numerology_reports_used", None)
        if product_limit is not None and int(product_limit or 0) > 0:
            limit = int(product_limit or 0)
            used = int(product_used or 0)
    else:
        product_limit = getattr(sub, "vastu_reports_limit", None)
        product_used = getattr(sub, "vastu_reports_used", None)
        if product_limit is not None and int(product_limit or 0) > 0:
            limit = int(product_limit or 0)
            used = int(product_used or 0)

    if used >= limit:
        return False, f"Report limit exceeded for {product} on this plan"

    return True, sub


def increment_usage(db: Session, user_id: int, product: str = "vastu"):
    """Increase report usage count after successful report generation."""
    if product not in VALID_PRODUCTS:
        return False

    sub = get_active_subscription(db, user_id)
    if not sub:
        return False

    # Always keep legacy counter in sync (admin UI / older clients)
    sub.reports_used = (sub.reports_used or 0) + 1

    if product == "numerology" and hasattr(sub, "numerology_reports_used"):
        sub.numerology_reports_used = (sub.numerology_reports_used or 0) + 1
    elif product == "vastu" and hasattr(sub, "vastu_reports_used"):
        sub.vastu_reports_used = (sub.vastu_reports_used or 0) + 1

    db.commit()
    return True


def reset_monthly_usage(db: Session):
    subscriptions = db.query(Subscription).all()
    for sub in subscriptions:
        sub.reports_used = 0
        if hasattr(sub, "vastu_reports_used"):
            sub.vastu_reports_used = 0
        if hasattr(sub, "numerology_reports_used"):
            sub.numerology_reports_used = 0
    db.commit()
    return True
