from sqlalchemy import Column, Integer, String, Boolean, Text
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    # White-label
    logo = Column(String(255))
    header_title = Column(String(255))
    header_subtitle = Column(String(255))
    address = Column(Text)
    footer_text = Column(Text)

    is_active = Column(Boolean, default=True)