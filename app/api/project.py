from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.project import Project

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_project(data: dict, db: Session = Depends(get_db)):

    project = Project(
        user_id=data["user_id"],
        name=data["name"],
        image_path=data.get("image_path"),
        rotation_angle=data.get("rotation_angle", 0),
        starting_degree=data.get("starting_degree", 0)
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "success": True,
        "project_id": project.id
    }