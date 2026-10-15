# app/api/plans.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.plan import Plan

router = APIRouter(prefix="/plans", tags=["Plans"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _plan_to_dict(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "price": float(plan.price),
        "discountprice": float(plan.discountprice) if plan.discountprice is not None else None,
        "duration_days": plan.duration_days,
        "report_limit": plan.report_limit,
        "product_access": getattr(plan, "product_access", None) or "both",
        "vastu_report_limit": getattr(plan, "vastu_report_limit", None),
        "numerology_report_limit": getattr(plan, "numerology_report_limit", None),
        "is_whitelabel": plan.is_whitelabel,
        "features": plan.features,
    }


@router.get("/")
def get_all_plans(
    product: Optional[str] = Query(
        None,
        description="Filter by product: vastu | numerology | both (returns matching + both)",
    ),
    db: Session = Depends(get_db),
):
    plans = db.query(Plan).all()
    if product:
        product = product.lower()
        if product not in ("vastu", "numerology", "both"):
            raise HTTPException(400, "product must be vastu, numerology, or both")
        plans = [
            p
            for p in plans
            if (getattr(p, "product_access", None) or "both").lower() in (product, "both")
            or product == "both"
        ]
    return [_plan_to_dict(p) for p in plans]


@router.get("/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_dict(plan)
