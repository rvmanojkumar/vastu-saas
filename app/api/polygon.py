from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.polygon import Polygon

router = APIRouter(prefix="/polygons", tags=["Polygons"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def save_polygon(data: dict, db: Session = Depends(get_db)):

    polygon = Polygon(
        project_id=data["project_id"],
        coordinates=data["coordinates"]
    )

    db.add(polygon)
    db.commit()
    db.refresh(polygon)

    return {
        "success": True,
        "polygon_id": polygon.id
    }