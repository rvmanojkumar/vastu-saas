# app/api/subscription_api.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.models.subscription import Subscription
from app.models.user import User
from app.core.security import get_current_admin
from app.models.user import User as UserModel

router = APIRouter(prefix="/api/admin/subscriptions", tags=["Admin Subscriptions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/assign/{user_id}")
def assign_subscription(
    user_id: int,
    plan_name: str,
    reports_limit: int,
    duration_days: int = 30,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin)  # Admin only
):
    """Assign subscription to user (Admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Deactivate old subscription
    db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).update({"status": "expired"})
    
    # Create new subscription
    subscription = Subscription(
        user_id=user_id,
        plan_name=plan_name,
        status="active",
        reports_limit=reports_limit,
        reports_used=0,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=duration_days)
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return subscription

@router.get("/user/{user_id}")
def get_user_subscription(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin)  # Admin only
):
    """Get user subscription details (Admin only)"""
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        return {"message": "No active subscription"}
    
    return subscription

@router.get("/all")
def get_all_subscriptions(
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin)
):
    """Get all subscriptions (Admin only)"""
    
    subscriptions = db.query(Subscription).all()
    return subscriptions