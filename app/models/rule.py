from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True)

    entity_type = Column(String(20))  
    # room | object

    entity_name = Column(String(100))  
    # Bedroom, Kitchen, Bed, Stove

    direction_system = Column(String(10))  
    # 16 | 32 | CENTER

    direction_value = Column(String(50))  
    # NE, SW, etc.

    result = Column(String(20))  
    # good | bad | neutral

    title = Column(String(255))
    description = Column(Text)
    remedy = Column(Text)

    # NEW FIELDS (IMPORTANT)
    color = Column(String(50), nullable=True)
    therapy = Column(Text, nullable=True)