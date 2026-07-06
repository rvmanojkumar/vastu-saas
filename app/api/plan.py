# app/api/plans.py
from fastapi import APIRouter, Depends, HTTPException
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
        "is_whitelabel": plan.is_whitelabel,
        "features": plan.features,
    }


@router.get("/")
def get_all_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).all()
    return [_plan_to_dict(p) for p in plans]


@router.get("/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_dict(plan)