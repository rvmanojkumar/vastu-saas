from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.promocode import Promocode


def plan_base_amount(plan: Plan) -> Decimal:
    """Charge base: discountprice if present, else price."""
    if plan.discountprice is not None:
        return Decimal(str(plan.discountprice))
    return Decimal(str(plan.price))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_discount(
    base: Decimal, discount_type: str, discount_value: Decimal
) -> Tuple[Decimal, Decimal]:
    """
    Returns (final_amount, discount_applied).
    Raises HTTPException if discount would make amount free / invalid.
    """
    dtype = (discount_type or "").lower().strip()
    value = Decimal(str(discount_value))

    if dtype == "percentage":
        if value <= 0 or value >= 100:
            raise HTTPException(
                status_code=400,
                detail="Promocode percentage must be greater than 0 and less than 100",
            )
        discount = _money(base * value / Decimal("100"))
    elif dtype == "amount":
        if value <= 0:
            raise HTTPException(status_code=400, detail="Promocode amount must be greater than 0")
        discount = _money(value)
    else:
        raise HTTPException(status_code=400, detail="Invalid discount type")

    final = _money(base - discount)
    if final <= 0:
        raise HTTPException(
            status_code=400,
            detail="Promocode cannot make the amount free. Please use a different code.",
        )
    if discount >= base:
        raise HTTPException(
            status_code=400,
            detail="Promocode cannot make the amount free. Please use a different code.",
        )
    return final, discount


def get_promocode_by_code(db: Session, code: str) -> Optional[Promocode]:
    normalized = (code or "").strip().upper()
    if not normalized:
        return None
    return db.query(Promocode).filter(Promocode.code == normalized).first()


def validate_promocode_for_plan(
    db: Session, code: str, plan_id: int
) -> Tuple[Promocode, Plan, Decimal, Decimal, Decimal]:
    """
    Validate promocode against plan and usage rules.
    Returns (promo, plan, base_amount, final_amount, discount_applied).
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    promo = get_promocode_by_code(db, code)
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid promocode")

    if (promo.status or "").lower() != "active":
        raise HTTPException(status_code=400, detail="Promocode is inactive")

    if promo.ends_on < date.today():
        raise HTTPException(status_code=400, detail="Promocode has expired")

    if promo.used_count >= promo.max_usage:
        raise HTTPException(status_code=400, detail="Promocode usage limit reached")

    if promo.plan_id != plan_id:
        raise HTTPException(
            status_code=400, detail="Promocode not valid for this plan"
        )

    base = plan_base_amount(plan)
    final, discount = apply_discount(base, promo.discount_type, promo.discount_value)
    return promo, plan, base, final, discount
