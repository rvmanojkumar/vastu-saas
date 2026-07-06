
import os
import uuid
import logging
from datetime import datetime, timedelta
 
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
from app.models.user import User as UserModel
from app.core.security import get_current_user  # <-- adjust if your dependency has a different name
 
load_dotenv()
logger = logging.getLogger(__name__)
 
router = APIRouter(prefix="/payments", tags=["Payments"])
 
RAZORPAY_KEY_ID = os.getenv("RazorPay_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RazorPay_KEY_SECRET")
 
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
 
 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
 
 
# ---------- Request/response bodies ----------
 
class CreateOrderRequest(BaseModel):
    plan_id: int
 
 
class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
 
 
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
    """
    plan = db.query(Plan).filter(Plan.id == body.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
 
    # Use discountprice if set, otherwise the regular price
    charge_amount_rupees = plan.discountprice if plan.discountprice is not None else plan.price
    amount_paise = int(round(float(charge_amount_rupees) * 100))
 
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
        "key": RAZORPAY_KEY_ID,   # safe to expose, it's the public Key ID
        "plan_name": plan.name,
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
    and creates the user's subscription. Never trust the client-side
    success callback alone — this recomputation is what actually confirms
    the payment is genuine.
    """
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
 
    # Fetch extra details (payment method, raw response) for record-keeping
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
    db.commit()
    db.refresh(payment)
 
    # Expire any existing active subscription before creating the new one
    db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active",
    ).update({"status": "expired"})
 
    subscription = Subscription(
        user_id=current_user.id,
        plan_id=payment.plan_id,
        plan_name=payment.plan_name,
        status="active",
        reports_limit=payment.report_limit,
        reports_used=0,
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
            "plan_name": subscription.plan_name,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "reports_limit": subscription.reports_limit,
        },
    }
