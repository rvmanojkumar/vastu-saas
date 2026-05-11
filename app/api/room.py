from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.report_entity import ReportEntity

router = APIRouter(prefix="/rooms", tags=["Rooms"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_all_rooms(db: Session = Depends(get_db)):
    """Get all available room types for Vastu analysis"""
    
    rooms = db.query(ReportEntity).filter(
        ReportEntity.category == "room",
        ReportEntity.is_active == True
    ).order_by(ReportEntity.sort_order).all()
    
    return rooms

@router.get("/{room_slug}/directions")
def get_room_direction_rules(
    room_slug: str,
    direction_system: str = "16",
    db: Session = Depends(get_db)
):
    """Get all direction rules for a specific room"""
    
    room = db.query(ReportEntity).filter(
        ReportEntity.slug == room_slug,
        ReportEntity.category == "room"
    ).first()
    
    if not room:
        return {"error": "Room not found"}
    
    # This would join with ReportRule table if you have it
    # For now, return basic structure
    return {
        "room": room.name,
        "directions": []
    }