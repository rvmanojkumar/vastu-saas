from app.db.base import Base
from sqlalchemy import Column, Integer, String, Text,Index


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
    ratings = Column(Integer, default=0)

    # NEW FIELDS (IMPORTANT)
    color = Column(String(50), nullable=True)
    therapy = Column(Text, nullable=True)

    __table_args__ = (
    Index(
        "idx_rule_lookup",
        "entity_type",
        "entity_name",
        "direction_system",
        "direction_value"
    ),
)