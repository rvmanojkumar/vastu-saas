from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.rule import Rule

router = APIRouter(prefix="/rules", tags=["Rules"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_rule(data: dict, db: Session = Depends(get_db)):

    rule = Rule(
        entity_type=data["entity_type"],
        entity_name=data["entity_name"],
        direction_system=data["direction_system"],
        direction_value=data["direction_value"],
        result=data["result"],
        title=data.get("title"),
        description=data.get("description"),
        remedy=data.get("remedy")
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return {"message": "Rule created", "id": rule.id}