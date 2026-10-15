from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Numeric, Text
from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    discountprice = Column(Numeric(10, 2), nullable=True)
    duration_days = Column(Integer, nullable=False)
    features = Column(Text, nullable=True)
    is_whitelabel = Column(Integer, default=False)

    # Legacy combined limit (kept for backward compatibility / display)
    report_limit = Column(Integer, nullable=True)

    # Product scope: vastu | numerology | both
    product_access = Column(String(20), nullable=False, default="both")

    # Separate quotas per product (used when creating subscriptions)
    vastu_report_limit = Column(Integer, nullable=True, default=0)
    numerology_report_limit = Column(Integer, nullable=True, default=0)

    subscriptions = relationship("Subscription", back_populates="plan")
