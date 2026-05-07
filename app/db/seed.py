from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import *

from datetime import datetime, timedelta


def seed():
    db: Session = SessionLocal()

    # ✅ 1. CREATE USER FIRST
    user = User(
        id=1,
        name="Demo User",
        email="demo@test.com",
        phone="9999999999",
        password="hashed"
    )
    db.add(user)
    db.commit()   # 🔥 IMPORTANT
    db.refresh(user)

    # ✅ 2. CREATE PLAN
    plan = Plan(
        id=1,
        name="Pro Plan",
        price=999,
        duration_days=30,
        report_limit=20,
        is_whitelabel=True
    )
    db.add(plan)
    db.commit()

    # ✅ 3. CREATE SUBSCRIPTION
    sub = Subscription(
        user_id=user.id,
        plan_name="Pro Plan",
        status="active",
        reports_limit=20,
        reports_used=0,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30)
    )
    db.add(sub)
    db.commit()

    # ✅ 4. NOW CREATE PROJECT (AFTER USER EXISTS)
    project = Project(
        id=1,
        user_id=user.id,
        name="Demo Project",
        description="Test",
        image_path=None,
        rotation=0,
        starting_degree=0
    )
    db.add(project)
    db.commit()

    db.close()


if __name__ == "__main__":
    seed()