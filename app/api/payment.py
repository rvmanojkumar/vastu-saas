import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

import razorpay
from razorpay.errors import SignatureVerificationError
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.models.plan import Plan
from app.models.payment import Payment, PaymentStatus
from app.models.subscription import Subscription
from app.models.promocode import Promocode
from app.models.user import User as UserModel
from app.core.security import get_current_user
from app.services.subscription import quotas_from_plan
from app.services.promocode import (
    plan_base_amount,
    validate_promocode_for_plan,
)

load_dotenv(override=True)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


def _get_razorpay_client():
    """Always read credentials fresh from env to avoid stale module-level values."""
    key_id = os.getenv("RazorPay_KEY_ID")
    key_secret = os.getenv("RazorPay_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured")
    return razorpay.Client(auth=(key_id, key_secret)), key_id


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Request/response bodies ----------

class CreateOrderRequest(BaseModel):
    plan_id: int
    promocode: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class ValidatePromoRequest(BaseModel):
    plan_id: int
    promocode: str


# ---------- Validate promocode ----------

@router.post("/validate-promo")
def validate_promo(
    body: ValidatePromoRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    promo, plan, base, final, discount = validate_promocode_for_plan(
        db, body.promocode, body.plan_id
    )
    return {
        "valid": True,
        "message": "Promocode applied successfully",
        "code": promo.code,
        "plan_id": plan.id,
        "plan_name": plan.name,
        "discount_type": promo.discount_type,
        "discount_value": float(promo.discount_value),
        "original_amount": float(base),
        "discount_applied": float(discount),
        "final_amount": float(final),
    }


# ---------- Create order ----------

@router.post("/create-order")
def create_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Creates a Razorpay order for the given plan.
    The amount is ALWAYS derived from the plan on the server —
    never trust an amount sent by the client.
    Optional promocode is validated and applied server-side.
    """
    client, key_id = _get_razorpay_client()

    plan = db.query(Plan).filter(Plan.id == body.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    base_amount = plan_base_amount(plan)
    charge_amount_rupees = base_amount
    discount_applied = None
    promocode_id = None
    applied_code = None

    if body.promocode and body.promocode.strip():
        promo, plan, base_amount, final, discount = validate_promocode_for_plan(
            db, body.promocode, body.plan_id
        )
        charge_amount_rupees = final
        discount_applied = discount
        promocode_id = promo.id
        applied_code = promo.code

    amount_paise = int(round(float(charge_amount_rupees) * 100))
    if amount_paise < 100:
        raise HTTPException(
            status_code=400,
            detail="Payable amount must be at least ₹1",
        )

    transaction_reference = str(uuid.uuid4())

    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "receipt": transaction_reference,
        })
    except Exception as e:
        logger.exception("Razorpay order creation failed")
        raise HTTPException(status_code=502, detail="Could not create payment order") from e

    payment = Payment(
        user_id=current_user.id,
        plan_id=plan.id,
        plan_name=plan.name,
        plan_price=plan.price,
        duration_days=plan.duration_days,
        report_limit=plan.report_limit,
        is_whitelabel=plan.is_whitelabel or 0,
        amount=charge_amount_rupees,
        promocode_id=promocode_id,
        discount_applied=discount_applied,
        currency="INR",
        gateway="razorpay",
        transaction_reference=transaction_reference,
        razorpay_order_id=order["id"],
        status=PaymentStatus.created,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "order_id": order["id"],
        "amount": amount_paise,   # paise — what Razorpay checkout expects
        "currency": "INR",
        "key": key_id,
        "plan_name": plan.name,
        "original_amount": float(base_amount),
        "discount_applied": float(discount_applied) if discount_applied is not None else 0,
        "final_amount": float(charge_amount_rupees),
        "promocode": applied_code,
    }


# ---------- Verify payment + create subscription ----------

@router.post("/verify")
def verify_payment(
    body: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Verifies the Razorpay signature server-side, marks the payment as paid,
    increments promocode usage if applicable, and creates the subscription.
    """
    client, _ = _get_razorpay_client()

    payment = db.query(Payment).filter(
        Payment.razorpay_order_id == body.razorpay_order_id,
        Payment.user_id == current_user.id,
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if payment.status == PaymentStatus.paid:
        return {"message": "Payment already verified", "status": "paid"}

    params_dict = {
        "razorpay_order_id": body.razorpay_order_id,
        "razorpay_payment_id": body.razorpay_payment_id,
        "razorpay_signature": body.razorpay_signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except SignatureVerificationError:
        payment.status = PaymentStatus.failed
        payment.remarks = "Signature verification failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Payment verification failed")

    try:
        razorpay_payment = client.payment.fetch(body.razorpay_payment_id)
    except Exception:
        razorpay_payment = {}

    payment.razorpay_payment_id = body.razorpay_payment_id
    payment.razorpay_signature = body.razorpay_signature
    payment.status = PaymentStatus.paid
    payment.payment_method = razorpay_payment.get("method")
    payment.gateway_response = razorpay_payment
    payment.paid_at = datetime.utcnow()

    # Increment promocode usage only after successful payment
    if payment.promocode_id:
        promo = db.query(Promocode).filter(Promocode.id == payment.promocode_id).first()
        if promo:
            promo.used_count = (promo.used_count or 0) + 1

    db.commit()
    db.refresh(payment)

    db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active",
    ).update({"status": "expired"})

    plan = db.query(Plan).filter(Plan.id == payment.plan_id).first()
    access, vastu_limit, numerology_limit = quotas_from_plan(plan) if plan else (
        "both",
        payment.report_limit or 0,
        0,
    )

    subscription = Subscription(
        user_id=current_user.id,
        plan_id=payment.plan_id,
        status="active",
        reports_limit=vastu_limit if access != "numerology" else (payment.report_limit or 0),
        reports_used=0,
        vastu_reports_limit=vastu_limit,
        vastu_reports_used=0,
        numerology_reports_limit=numerology_limit,
        numerology_reports_used=0,
        product_access=access,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=payment.duration_days),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return {
        "message": "Payment verified and subscription activated",
        "status": "paid",
        "subscription": {
            "plan_id": subscription.plan_id,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "product_access": subscription.product_access,
            "reports_limit": subscription.reports_limit,
            "vastu_reports_limit": subscription.vastu_reports_limit,
            "numerology_reports_limit": subscription.numerology_reports_limit,
        },
    }
