# app/models/translation.py
from app.db.base import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    UniqueConstraint
)




class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True)

    table_name = Column(String(50), nullable=False)
    # direction
    # report_entity
    # report_rule

    record_id = Column(Integer, nullable=False)

    language_id = Column(
        Integer,
        ForeignKey("languages.id"),
        nullable=False
    )

    field_name = Column(String(100), nullable=False)
    # name
    # prediction
    # remedies
    # therapies
    # colors
    # notes

    value = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'table_name',
            'record_id',
            'language_id',
            'field_name',
            name='uq_translation'
        ),
    )