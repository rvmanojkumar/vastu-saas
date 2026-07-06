import enum
from sqlalchemy import (
    Column, BigInteger, String, Numeric, Integer, Enum, JSON, Text, DateTime
)
from sqlalchemy.sql import func
from app.db.base import Base  # <-- adjust if your Base lives elsewhere
 
 
class PaymentStatus(str, enum.Enum):
    created = "created"
    paid = "paid"
    failed = "failed"
    cancelled = "cancelled"
    refunded = "refunded"
 
 
class PaymentGateway(str, enum.Enum):
    razorpay = "razorpay"
 
 
class Payment(Base):
    __tablename__ = "payments"
 
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    plan_id = Column(BigInteger, nullable=False)
    plan_name = Column(String(100), nullable=False)
    plan_price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)
    report_limit = Column(Integer, nullable=False)
    is_whitelabel = Column(Integer, nullable=True, default=0)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=True, default="INR")
    gateway = Column(Enum(PaymentGateway), nullable=True, default=PaymentGateway.razorpay)
    transaction_reference = Column(String(100), nullable=False)
    razorpay_order_id = Column(String(100), nullable=True, unique=True)
    razorpay_payment_id = Column(String(100), nullable=True, unique=True)
    razorpay_signature = Column(String(255), nullable=True)
    payment_method = Column(String(50), nullable=True)
    status = Column(Enum(PaymentStatus), nullable=True, default=PaymentStatus.created)
    gateway_response = Column(JSON, nullable=True)
    remarks = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
 