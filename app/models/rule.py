from app.db.base import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Index,
    Float,
    Numeric,
)


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True)

    entity_type = Column(String(20))
    entity_name = Column(String(100))

    direction_system = Column(String(10))
    direction_value = Column(String(50))

    result = Column(String(20))

    title = Column(String(255))
    description_en = Column(Text)
    description_mr = Column(Text, nullable=True)  # ← add
    description_hi = Column(Text, nullable=True)  # ← add
    remedy_en = Column(Text)
    remedy_mr = Column(Text, nullable=True)        # ← add
    remedy_hi = Column(Text, nullable=True)       

    ratings = ratings = Column(Numeric(3, 1), default=0)

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