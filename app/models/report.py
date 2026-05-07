from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, DateTime
from datetime import datetime
from app.db.base import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    pdf_path = Column(String(255))
    is_whitelabel = Column(Boolean)

    created_at = Column(DateTime, default=datetime.utcnow)