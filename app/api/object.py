from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.object import Object

from app.services.geometry.engine import analyze_point
from app.services.geometry.utils import calculate_center_from_coords
from app.services.rule_engine import evaluate_rule

router = APIRouter(prefix="/objects", tags=["Objects"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_object(data: dict, db: Session = Depends(get_db)):

    coords = data["coordinates"]
    polygon = data["polygon"]

    center = calculate_center_from_coords(coords)

    analysis = analyze_point(
        [(p["x"], p["y"]) for p in polygon],
        center,
        data.get("starting_degree", 0)
    )

    rule_result = evaluate_rule(
        db=db,
        entity_type="object",
        entity_name=data["name"],
        direction_system="16",
        direction_value=analysis["direction_16"]
    )

    obj = Object(
        project_id=data["project_id"],
        name=data["name"],
        coordinates=coords,
        center_x=center[0],
        center_y=center[1],
        direction_16=analysis["direction_16"],
        direction_32=analysis["direction_32"]
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)

    return {
        "success": True,
        "object_id": obj.id,
        "geometry": analysis,
        "rule": rule_result
    }