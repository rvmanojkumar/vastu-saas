from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

from app.models.room import Room
from app.models.polygon import Polygon

from app.services.geometry.engine import analyze_point
from app.services.geometry.utils import calculate_center_from_coords
from app.services.rule_engine import evaluate_rule


router = APIRouter(prefix="/rooms", tags=["Rooms"])


# =========================
# DB DEPENDENCY
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# CREATE ROOM
# =========================
@router.post("/")
def create_room(data: dict, db: Session = Depends(get_db)):

    try:
        """
        Expected payload:

        {
            "project_id": 1,
            "name": "Bedroom",
            "coordinates": [{"x":10,"y":20}, ...],
            "polygon": [{"x":0,"y":0}, ...],
            "starting_degree": 0
        }
        """

        # -------------------------
        # INPUT DATA
        # -------------------------
        project_id = data["project_id"]
        name = data["name"]
        coords = data["coordinates"]
        polygon = data["polygon"]
        starting_degree = data.get("starting_degree", 0)

        # -------------------------
        # CONVERT TO TUPLES
        # -------------------------
        coords_tuples = [(p["x"], p["y"]) for p in coords]
        polygon_tuples = [(p["x"], p["y"]) for p in polygon]

        # -------------------------
        # CALCULATE CENTER
        # -------------------------
        center = calculate_center_from_coords(coords)

        if not center:
            raise HTTPException(status_code=400, detail="Invalid coordinates")

        # -------------------------
        # GEOMETRY ANALYSIS
        # -------------------------
        analysis = analyze_point(
            polygon_tuples,
            center,
            starting_degree
        )

        # -------------------------
        # RULE ENGINE
        # -------------------------
        rule_result = evaluate_rule(
            db=db,
            entity_type="room",
            entity_name=name,
            direction_system="16",
            direction_value=analysis.get("direction_16")
        )

        # -------------------------
        # SAVE ROOM
        # -------------------------
        room = Room(
            project_id=project_id,
            name=name,
            coordinates=coords,

            center_x=center[0],
            center_y=center[1],

            direction_16=analysis.get("direction_16"),
            direction_32=analysis.get("direction_32")
        )

        db.add(room)
        db.commit()
        db.refresh(room)

        # -------------------------
        # RESPONSE
        # -------------------------
        return {
            "success": True,
            "room_id": room.id,

            "geometry": {
                "center": center,
                "angle": analysis.get("angle"),
                "direction_16": analysis.get("direction_16"),
                "direction_32": analysis.get("direction_32"),
                "zone": analysis.get("zone")
            },

            "rule_analysis": rule_result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =========================
# GET ALL ROOMS (optional)
# =========================
@router.get("/{project_id}")
def get_rooms(project_id: int, db: Session = Depends(get_db)):

    rooms = db.query(Room).filter(Room.project_id == project_id).all()

    return {
        "project_id": project_id,
        "rooms": [
            {
                "id": r.id,
                "name": r.name,
                "direction_16": r.direction_16,
                "direction_32": r.direction_32
            }
            for r in rooms
        ]
    }