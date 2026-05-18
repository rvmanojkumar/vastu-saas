from app.db.base import Base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)

    plan_name = Column(String(100)) 
    status = Column(String(50), default="active")

    reports_limit = Column(Integer, default=10)
    reports_used = Column(Integer, default=0)

    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)