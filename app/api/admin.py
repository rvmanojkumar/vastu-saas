from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from app.db.session import SessionLocal
from app.models.user import User
from app.models.subscription import Subscription
from app.models.project import Project
from app.models.report import Report
from app.models.object import Object
from app.core.security import get_current_admin
from app.services.subscription import increment_usage
from app.models.rule import Rule
from app.core.cache import set_cached_rooms, set_cached_objects

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Pydantic schemas
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class SubscriptionAssign(BaseModel):
    plan_name: str
    reports_limit: int
    duration_days: int = 30

class BulkSubscriptionAssign(BaseModel):
    user_ids: List[int]
    plan_name: str
    reports_limit: int
    duration_days: int = 30

# ============= RULE SCHEMAS =============

class RuleCreate(BaseModel):
    entity_type: str
    entity_name: str
    direction_system: str
    direction_value: str

    result: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    remedy: Optional[str] = None
    ratings: Optional[int] = None
    color: Optional[str] = None
    therapy: Optional[str] = None


class RuleUpdate(BaseModel):
    result: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    remedy: Optional[str] = None
    ratings: Optional[int] = None
    color: Optional[str] = None
    therapy: Optional[str] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============= DASHBOARD STATISTICS =============
@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get admin dashboard statistics"""
    
    # User statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == "admin").count()
    new_users_today = db.query(User).filter(
        func.date(User.created_at) == datetime.utcnow().date()
    ).count()
    
    # Subscription statistics
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == "active",
        Subscription.end_date > datetime.utcnow()
    ).count()
    expired_subscriptions = db.query(Subscription).filter(
        Subscription.end_date < datetime.utcnow()
    ).count()
    
    # Report statistics
    total_reports = db.query(Report).count()
    reports_this_month = db.query(Report).filter(
        func.date(Report.created_at) >= datetime.utcnow().replace(day=1)
    ).count()
    
    # Project statistics
    total_projects = db.query(Project).count()
    total_objects = db.query(Object).count()
    
    # Revenue calculation (if you have payment table)
    # total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == "completed").scalar() or 0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users,
            "new_today": new_users_today
        },
        "subscriptions": {
            "active": active_subscriptions,
            "expired": expired_subscriptions
        },
        "reports": {
            "total": total_reports,
            "this_month": reports_this_month
        },
        "projects": {
            "total": total_projects,
            "total_objects": total_objects
        },
        # "revenue": total_revenue
    }

# ============= USER MANAGEMENT =============
@router.get("/users")
def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all users with pagination and filters"""
    
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%"))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Get subscription info for each user
    result = []
    for user in users:
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        ).first()
        
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "subscription": {
                "has_active": subscription is not None,
                "plan_name": subscription.plan_name if subscription else None,
                "reports_limit": subscription.reports_limit if subscription else 0,
                "reports_used": subscription.reports_used if subscription else 0,
                "remaining": (subscription.reports_limit - subscription.reports_used) if subscription else 0,
                "expires_on": subscription.end_date if subscription else None
            } if subscription else None
        })
    
    return {
        "users": result,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get detailed user information"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Get subscription history
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).order_by(Subscription.start_date.desc()).all()
    
    # Get projects
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    
    # Get reports
    reports = db.query(Report).filter(Report.project_id.in_([p.id for p in projects])).all()
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "logo": user.logo,
        "header_title": user.header_title,
        "header_subtitle": user.header_subtitle,
        "address": user.address,
        "footer_text": user.footer_text,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "subscriptions": [
            {
                "id": sub.id,
                "plan_name": sub.plan_name,
                "status": sub.status,
                "reports_limit": sub.reports_limit,
                "reports_used": sub.reports_used,
                "start_date": sub.start_date,
                "end_date": sub.end_date
            } for sub in subscriptions
        ],
        "projects_count": len(projects),
        "reports_count": len(reports)
    }

@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update user information"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Prevent admin from demoting themselves
    if user.id == current_admin.id and user_data.role == "user":
        raise HTTPException(400, "Cannot demote yourself")
    
    # Update fields
    for field, value in user_data.dict(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return {"message": "User updated successfully", "user": user}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete user (soft delete by setting is_active=False)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Prevent admin from deleting themselves
    if user.id == current_admin.id:
        raise HTTPException(400, "Cannot delete yourself")
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}

# ============= SUBSCRIPTION MANAGEMENT =============
@router.post("/users/{user_id}/subscription")
def assign_subscription(
    user_id: int,
    subscription_data: SubscriptionAssign,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Assign subscription to user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Deactivate old subscriptions
    db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).update({"status": "expired"})
    
    # Create new subscription
    new_subscription = Subscription(
        user_id=user_id,
        plan_name=subscription_data.plan_name,
        status="active",
        reports_limit=subscription_data.reports_limit,
        reports_used=0,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=subscription_data.duration_days)
    )
    
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)
    
    return {
        "message": "Subscription assigned successfully",
        "subscription": new_subscription
    }

@router.post("/subscriptions/bulk-assign")
def bulk_assign_subscription(
    data: BulkSubscriptionAssign,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Assign subscription to multiple users"""
    
    results = []
    for user_id in data.user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            results.append({"user_id": user_id, "status": "failed", "reason": "User not found"})
            continue
        
        # Deactivate old subscriptions
        db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).update({"status": "expired"})
        
        # Create new subscription
        new_subscription = Subscription(
            user_id=user_id,
            plan_name=data.plan_name,
            status="active",
            reports_limit=data.reports_limit,
            reports_used=0,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=data.duration_days)
        )
        
        db.add(new_subscription)
        results.append({"user_id": user_id, "status": "success"})
    
    db.commit()
    
    return {
        "message": f"Bulk subscription assigned",
        "results": results
    }

@router.get("/subscriptions/all")
def get_all_subscriptions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all subscriptions with user details"""
    
    query = db.query(Subscription, User).join(User, Subscription.user_id == User.id)
    
    if status:
        query = query.filter(Subscription.status == status)
    
    subscriptions = query.order_by(Subscription.start_date.desc()).all()
    
    result = []
    for sub, user in subscriptions:
        result.append({
            "id": sub.id,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "plan_name": sub.plan_name,
            "status": sub.status,
            "reports_limit": sub.reports_limit,
            "reports_used": sub.reports_used,
            "remaining": sub.reports_limit - sub.reports_used,
            "start_date": sub.start_date,
            "end_date": sub.end_date
        })
    
    return result

# ============= ANALYTICS =============
@router.get("/analytics/user-growth")
def get_user_growth(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get user growth over time"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        next_date = date + timedelta(days=1)
        
        count = db.query(User).filter(
            User.created_at >= date,
            User.created_at < next_date
        ).count()
        
        results.append({
            "date": date.strftime("%Y-%m-%d"),
            "count": count
        })
    
    return results

@router.get("/analytics/report-usage")
def get_report_usage(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get report generation statistics"""
    
    # Reports by plan
    reports_by_plan = db.query(
        Subscription.plan_name,
        func.count(Report.id).label('report_count')
    ).join(
        Subscription, Subscription.user_id == Report.project_id  # Adjust join as needed
    ).group_by(Subscription.plan_name).all()
    
    # Reports by month (last 12 months)
    reports_by_month = []
    for i in range(12):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
        month_start = month_start.replace(day=1, hour=0, minute=0, second=0)
        
        count = db.query(Report).filter(
            Report.created_at >= month_start,
            Report.created_at < month_start + timedelta(days=32)
        ).count()
        
        reports_by_month.append({
            "month": month_start.strftime("%B %Y"),
            "count": count
        })
    
    return {
        "by_plan": [{"plan": p[0], "count": p[1]} for p in reports_by_plan],
        "by_month": reports_by_month
    }

# ============= RULE MANAGEMENT =============

@router.get("/rules")
def get_rules(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    entity_type: Optional[str] = None,
    result: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    
    query = db.query(Rule)

    if search:
        query = query.filter(
            (Rule.entity_name.ilike(f"%{search}%")) |
            (Rule.title.ilike(f"%{search}%")) |
            (Rule.direction_value.ilike(f"%{search}%"))
        )

    if entity_type:
        query = query.filter(Rule.entity_type == entity_type)

    if result:
        query = query.filter(Rule.result == result)

    total = query.count()

    rules = query.order_by(Rule.id.desc()) \
        .offset((page - 1) * limit) \
        .limit(limit) \
        .all()

    return {
        "rules": rules,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.post("/rules")
def create_rule(
    data: RuleCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    rule = Rule(
        entity_type=data.entity_type,
        entity_name=data.entity_name,
        direction_system=data.direction_system,
        direction_value=data.direction_value,

        result=data.result,
        title=data.title,
        description=data.description,
        remedy=data.remedy,
        ratings=data.ratings,
        color=data.color,
        therapy=data.therapy,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)
    refresh_rooms_cache(db)
    refresh_objects_cache(db)
    return {
        "message": "Rule created successfully",
        "id": rule.id
    }


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    data: RuleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    rule = db.query(Rule).filter(
        Rule.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(404, "Rule not found")

    update_data = data.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)

    return {
        "message": "Rule updated successfully"
    }
@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    rule = db.query(Rule).filter(
        Rule.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(404, "Rule not found")

    db.delete(rule)
    db.commit()
    refresh_rooms_cache(db)
    refresh_objects_cache(db)

    return {
        "message": "Rule deleted successfully"
    }

@router.get("/rules/distinct")
def get_distinct_entities(
    entity_type: str = Query(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    entities = db.query(Rule.entity_name).filter(
        Rule.entity_type == entity_type
    ).distinct().all()

    return [
    {
        "entity_name": e[0],
        "entity_type": entity_type
    }
    for e in entities
]
@router.get("/rules/by-entity")
def get_rules_by_entity(
    entity_type: str,
    entity_name: str,
    direction_system: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    rules = db.query(Rule).filter(
        Rule.entity_type == entity_type,
        Rule.entity_name == entity_name,
        Rule.direction_system == direction_system
    ).all()

    return [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_name": r.entity_name,
            "direction_system": r.direction_system,
            "direction_value": r.direction_value,

            "result": r.result,
            "title": r.title,
            "description": r.description,
            "remedy": r.remedy,
            "ratings": r.ratings,
            "color": r.color,
            "therapy": r.therapy,
        }
        for r in rules
    ]

#GET SINGLE RULE
@router.get("/rules/{rule_id}")
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    rule = db.query(Rule).filter(Rule.id == rule_id).first()

    if not rule:
        raise HTTPException(404, "Rule not found")

    return rule

def refresh_rooms_cache(db):
    rooms = (
        db.query(Rule.entity_name)
        .filter(Rule.entity_type == "room")
        .distinct()
        .order_by(Rule.entity_name)
        .all()
    )

    room_list = [r[0] for r in rooms if r[0]]

    set_cached_rooms(room_list)
def refresh_objects_cache(db):
    objects = (
        db.query(Rule.entity_name)
        .filter(Rule.entity_type == "object")
        .distinct()
        .order_by(Rule.entity_name)
        .all()
    )

    object_list = [r[0] for r in objects if r[0]]

    set_cached_objects(object_list)


