from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.rule import Rule
from app.models.plan import Plan
from app.models.promocode import Promocode
from app.models.payment import Payment, PaymentStatus
from app.core.cache import set_cached_rooms, set_cached_objects, invalidate_rules_cache
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta, date
from decimal import Decimal
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
    description_en: Optional[str] = None
    description_hi: Optional[str] = None
    description_mr: Optional[str] = None
    remedy_en: Optional[str] = None
    remedy_hi: Optional[str] = None
    remedy_mr: Optional[str] = None
    ratings: Optional[float] = None
    color: Optional[str] = None
    therapy: Optional[str] = None


class RuleUpdate(BaseModel):
    result: Optional[str] = None
    title: Optional[str] = None
    description_en: Optional[str] = None
    description_hi: Optional[str] = None
    description_mr: Optional[str] = None
    remedy_en: Optional[str] = None
    remedy_hi: Optional[str] = None
    remedy_mr: Optional[str] = None
    ratings: Optional[float] = None
    color: Optional[str] = None
    therapy: Optional[str] = None


class PromocodeCreate(BaseModel):
    code: str
    plan_id: int
    discount_type: str  # percentage | amount
    discount_value: float
    max_usage: int
    ends_on: date
    status: str = "active"


class PromocodeUpdate(BaseModel):
    code: Optional[str] = None
    plan_id: Optional[int] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    max_usage: Optional[int] = None
    ends_on: Optional[date] = None
    status: Optional[str] = None


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
    """Get all users with package, payment, promocode, and report usage."""

    query = db.query(User)

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

    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    result = []
    for user in users:
        subscription = (
            db.query(Subscription)
            .options(joinedload(Subscription.plan))
            .filter(
                Subscription.user_id == user.id,
                Subscription.status == "active",
            )
            .order_by(Subscription.id.desc())
            .first()
        )

        # Latest successful payment (for amount + promocode)
        payment = (
            db.query(Payment)
            .filter(
                Payment.user_id == user.id,
                Payment.status == PaymentStatus.paid,
            )
            .order_by(Payment.paid_at.desc(), Payment.id.desc())
            .first()
        )

        promo_code = None
        if payment and payment.promocode_id:
            promo = (
                db.query(Promocode)
                .filter(Promocode.id == payment.promocode_id)
                .first()
            )
            promo_code = promo.code if promo else None

        plan_name = None
        if subscription and subscription.plan:
            plan_name = subscription.plan.name
        elif payment:
            plan_name = payment.plan_name

        reports_generated = (
            db.query(func.count(Report.id))
            .join(Project, Project.id == Report.project_id)
            .filter(Project.user_id == user.id)
            .scalar()
            or 0
        )

        # Prefer subscription usage counter when present (quota tracker)
        reports_used = (
            subscription.reports_used if subscription else reports_generated
        )

        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "plan_name": plan_name,
            "amount_paid": float(payment.amount) if payment and payment.amount is not None else None,
            "promocode": promo_code,
            "reports_generated": int(reports_generated),
            "reports_used": int(reports_used or 0),
            "reports_limit": int(subscription.reports_limit) if subscription else 0,
            "subscription": {
                "has_active": True,
                "plan_id": subscription.plan_id,
                "plan_name": plan_name,
                "reports_limit": subscription.reports_limit,
                "reports_used": subscription.reports_used,
                "remaining": (subscription.reports_limit or 0) - (subscription.reports_used or 0),
                "expires_on": subscription.end_date,
                "status": subscription.status,
            } if subscription else None,
            "payment": {
                "id": payment.id,
                "plan_name": payment.plan_name,
                "amount": float(payment.amount) if payment.amount is not None else None,
                "discount_applied": float(payment.discount_applied) if payment.discount_applied is not None else None,
                "promocode": promo_code,
                "paid_at": payment.paid_at,
                "status": payment.status.value if payment.status else None,
            } if payment else None,
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
        description_en=data.description_en,
        description_hi=data.description_hi,
        description_mr=data.description_mr,
        remedy_en=data.remedy_en,
        remedy_hi=data.remedy_hi,
        remedy_mr=data.remedy_mr,
        ratings=data.ratings,
        color=data.color,
        therapy=data.therapy,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)
    refresh_rooms_cache(db)
    refresh_objects_cache(db)
    invalidate_rules_cache()
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
    invalidate_rules_cache()

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
    invalidate_rules_cache()

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
            "description_en": r.description_en,
            "description_hi": r.description_hi,
            "description_mr": r.description_mr,
            "remedy_en": r.remedy_en,
            "remedy_hi": r.remedy_hi,
            "remedy_mr": r.remedy_mr,
            "ratings": float(r.ratings) if r.ratings is not None else None,
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


# ============= PROMOCODES =============

def _serialize_promocode(p: Promocode) -> dict:
    plan_name = p.plan.name if p.plan else None
    return {
        "id": p.id,
        "code": p.code,
        "plan_id": p.plan_id,
        "plan_name": plan_name,
        "discount_type": p.discount_type,
        "discount_value": float(p.discount_value) if p.discount_value is not None else None,
        "max_usage": p.max_usage,
        "used_count": p.used_count,
        "ends_on": p.ends_on.isoformat() if p.ends_on else None,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _validate_promo_payload(
    discount_type: str,
    discount_value: float,
    max_usage: int,
    status: str,
    plan_id: int,
    db: Session,
):
    dtype = (discount_type or "").lower().strip()
    if dtype not in ("percentage", "amount"):
        raise HTTPException(400, "discount_type must be 'percentage' or 'amount'")

    if discount_value is None or float(discount_value) <= 0:
        raise HTTPException(400, "discount_value must be greater than 0")

    if dtype == "percentage" and float(discount_value) >= 100:
        raise HTTPException(400, "percentage discount must be less than 100")

    if max_usage is None or int(max_usage) < 1:
        raise HTTPException(400, "max_usage must be at least 1")

    st = (status or "").lower().strip()
    if st not in ("active", "inactive"):
        raise HTTPException(400, "status must be 'active' or 'inactive'")

    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")

    return dtype, st


@router.get("/promocodes")
def list_promocodes(
    status: Optional[str] = None,
    plan_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(Promocode).options(joinedload(Promocode.plan))
    if status:
        query = query.filter(Promocode.status == status.lower().strip())
    if plan_id:
        query = query.filter(Promocode.plan_id == plan_id)
    promos = query.order_by(Promocode.id.desc()).all()
    return [_serialize_promocode(p) for p in promos]


@router.post("/promocodes")
def create_promocode(
    data: PromocodeCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    dtype, st = _validate_promo_payload(
        data.discount_type,
        data.discount_value,
        data.max_usage,
        data.status,
        data.plan_id,
        db,
    )
    code = (data.code or "").strip().upper()
    if not code:
        raise HTTPException(400, "code is required")

    exists = db.query(Promocode).filter(Promocode.code == code).first()
    if exists:
        raise HTTPException(400, "Promocode already exists")

    promo = Promocode(
        code=code,
        plan_id=data.plan_id,
        discount_type=dtype,
        discount_value=Decimal(str(data.discount_value)),
        max_usage=int(data.max_usage),
        used_count=0,
        ends_on=data.ends_on,
        status=st,
    )
    db.add(promo)
    db.commit()
    promo = (
        db.query(Promocode)
        .options(joinedload(Promocode.plan))
        .filter(Promocode.id == promo.id)
        .first()
    )
    return {"message": "Promocode created", "promocode": _serialize_promocode(promo)}


@router.put("/promocodes/{promo_id}")
def update_promocode(
    promo_id: int,
    data: PromocodeUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    promo = db.query(Promocode).filter(Promocode.id == promo_id).first()
    if not promo:
        raise HTTPException(404, "Promocode not found")

    payload = data.dict(exclude_unset=True)

    plan_id = payload.get("plan_id", promo.plan_id)
    discount_type = payload.get("discount_type", promo.discount_type)
    discount_value = float(
        payload.get("discount_value", promo.discount_value)
    )
    max_usage = int(payload.get("max_usage", promo.max_usage))
    status = payload.get("status", promo.status)

    dtype, st = _validate_promo_payload(
        discount_type, discount_value, max_usage, status, plan_id, db
    )

    if "code" in payload:
        code = (payload["code"] or "").strip().upper()
        if not code:
            raise HTTPException(400, "code is required")
        exists = (
            db.query(Promocode)
            .filter(Promocode.code == code, Promocode.id != promo_id)
            .first()
        )
        if exists:
            raise HTTPException(400, "Promocode already exists")
        promo.code = code

    promo.plan_id = plan_id
    promo.discount_type = dtype
    promo.discount_value = Decimal(str(discount_value))
    promo.max_usage = max_usage
    promo.status = st
    if "ends_on" in payload:
        promo.ends_on = payload["ends_on"]

    if promo.max_usage < promo.used_count:
        raise HTTPException(
            400, "max_usage cannot be less than current used_count"
        )

    db.commit()
    promo = (
        db.query(Promocode)
        .options(joinedload(Promocode.plan))
        .filter(Promocode.id == promo.id)
        .first()
    )
    return {"message": "Promocode updated", "promocode": _serialize_promocode(promo)}


@router.delete("/promocodes/{promo_id}")
def delete_promocode(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    promo = db.query(Promocode).filter(Promocode.id == promo_id).first()
    if not promo:
        raise HTTPException(404, "Promocode not found")

    # Soft-delete: deactivate so payment history stays valid
    promo.status = "inactive"
    db.commit()
    return {"message": "Promocode deactivated"}


