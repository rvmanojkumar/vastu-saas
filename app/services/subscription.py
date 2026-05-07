from sqlalchemy.orm import Session
from datetime import datetime

from app.models.subscription import Subscription


# =========================
# CHECK IF USER CAN GENERATE REPORT
# =========================
def check_subscription(db: Session, user_id: int):
    """
    Validates user subscription for report generation
    """

    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    # -------------------------
    # NO SUBSCRIPTION
    # -------------------------
    if not sub:
        return False, "No active subscription found"

    # -------------------------
    # STATUS CHECK
    # -------------------------
    if sub.status != "active":
        return False, "Subscription is not active"

    # -------------------------
    # EXPIRY CHECK
    # -------------------------
    if sub.end_date and sub.end_date < datetime.utcnow():
        return False, "Subscription expired"

    # -------------------------
    # USAGE LIMIT CHECK
    # -------------------------
    if sub.reports_used >= sub.reports_limit:
        return False, "Report limit exceeded for this plan"

    return True, sub


# =========================
# INCREMENT USAGE AFTER REPORT GENERATION
# =========================
def increment_usage(db: Session, user_id: int):
    """
    Increase report usage count after successful PDF generation
    """

    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not sub:
        return False

    sub.reports_used += 1
    db.commit()

    return True


# =========================
# RESET USAGE (OPTIONAL - FOR MONTHLY PLANS)
# =========================
def reset_monthly_usage(db: Session):
    """
    Can be used in a cron job (Celery beat / scheduler)
    """

    subscriptions = db.query(Subscription).all()

    for sub in subscriptions:
        sub.reports_used = 0

    db.commit()

    return True