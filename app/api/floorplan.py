import os
import shutil
import json
import math
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel  # ← ADD THIS IMPORT
from app.db.session import SessionLocal
from app.models.project import Project, ProjectStatus
from app.models.floorplan import ProjectImage, CanvasState
from app.models.polygon import Polygon, PolygonType
from app.models.user import User
from app.core.security import get_current_user
from datetime import datetime

# ============================================================
# ADD PYDANTIC MODELS HERE (after imports, before router)
# ============================================================

class RoomCreate(BaseModel):
    name: str
    coordinates: List[List[float]]
    centroid: Optional[Dict] = None
    direction: Optional[str] = None

class ObjectCreate(BaseModel):  # You might want this for objects too
    object_type: str
    position: List[float]
    direction: str
    rotation: int = 0
    room_id: Optional[int] = None  # Add this if you want to support specifying room

router = APIRouter(prefix="/api/floorplan", tags=["Floorplan"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_coordinates(coords, image_width, image_height):
    """Convert absolute pixel coordinates to normalized (0-1)"""
    return [[x / image_width, y / image_height] for x, y in coords]

def denormalize_coordinates(coords, image_width, image_height):
    """Convert normalized coordinates to absolute pixels"""
    return [[int(x * image_width), int(y * image_height)] for x, y in coords]

def compute_centroid(coords):
    """Calculate centroid of a polygon"""
    if not coords or len(coords) < 3:
        return None
    x_sum = sum(p[0] for p in coords)
    y_sum = sum(p[1] for p in coords)
    n = len(coords)
    return [x_sum / n, y_sum / n]

def get_direction_from_angle(angle, system="16"):
    """Convert angle to direction name based on 8/16/32 system"""
    if system == "8":
        sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        sector_size = 45
    elif system == "16":
        sectors = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        sector_size = 22.5
    else:  # 32
        sectors = [
            "N", "NbE", "NNE", "NEbn", "NE", "NEbE", "ENE", "EbnN",
            "E", "EbN", "ESE", "SEbE", "SE", "SEbS", "SSE", "SbE",
            "S", "SbW", "SSW", "SWbS", "SW", "SWbW", "WSW", "WbS",
            "W", "WbN", "WNW", "NWbW", "NW", "NWbN", "NNW", "NbW"
        ]
        sector_size = 11.25
    
    idx = int(((angle + sector_size / 2) % 360) / sector_size)
    return sectors[idx]

def calculate_direction(point, center, starting_degree=0, system="16"):
    """Calculate direction of a point relative to center"""
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    
    # Calculate angle in degrees from north (0 = north)
    angle = math.degrees(math.atan2(dx, -dy))  # Negative dy because y increases downward
    angle = (angle + 360) % 360
    
    # Apply starting degree offset (how much the north is rotated)
    angle = (angle - starting_degree + 360) % 360
    
    return get_direction_from_angle(angle, system)

def point_in_polygon(point, polygon):
    """Check if point is inside polygon using ray casting algorithm"""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside

# ============================================================
# IMAGE UPLOAD
# ============================================================

@router.post("/upload/{project_id}")
async def upload_floorplan(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload floor plan image for a project"""
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id, 
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found or not owned")
    
    # Create directory if not exists
    upload_dir = f"storage/projects/{project_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_ext = file.filename.split('.')[-1]
    filename = f"floorplan.{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Save to database
    project_image = ProjectImage(
        project_id=project_id,
        image_path=f"/storage/projects/{project_id}/{filename}",
        original_filename=file.filename
    )
    db.add(project_image)
    
    # Update project status
    project.status = ProjectStatus.UPLOADED
    db.commit()
    db.refresh(project_image)
    
    return {
        "success": True,
        "image_url": project_image.image_path,
        "image_id": project_image.id
    }

# ============================================================
# CANVAS STATE
# ============================================================

@router.post("/canvas-state/{project_id}")
def save_canvas_state(
    project_id: int,
    zoom: float = Query(1.0),
    pan_x: float = Query(0.0),
    pan_y: float = Query(0.0),
    rotation: float = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save canvas state (zoom, pan, rotation)"""
    
    # Verify ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    canvas_state = db.query(CanvasState).filter(
        CanvasState.project_id == project_id
    ).first()
    
    if not canvas_state:
        canvas_state = CanvasState(project_id=project_id)
        db.add(canvas_state)
    
    canvas_state.zoom = zoom
    canvas_state.pan_x = pan_x
    canvas_state.pan_y = pan_y
    canvas_state.rotation = rotation
    db.commit()
    
    return {"success": True}

@router.get("/canvas-state/{project_id}")
def get_canvas_state(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get canvas state"""
    
    canvas_state = db.query(CanvasState).filter(
        CanvasState.project_id == project_id
    ).first()
    
    if not canvas_state:
        return {
            "zoom": 1.0,
            "pan_x": 0.0,
            "pan_y": 0.0,
            "rotation": 0
        }
    
    return {
        "zoom": canvas_state.zoom,
        "pan_x": canvas_state.pan_x,
        "pan_y": canvas_state.pan_y,
        "rotation": canvas_state.rotation
    }

# ============================================================
# OUTER BOUNDARY
# ============================================================

@router.post("/boundary/{project_id}")
async def save_boundary(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save outer boundary polygon"""
    
    # Parse JSON body
    body = await request.json()
    coordinates = body.get('coordinates', [])
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Validate minimum 3 points
    if len(coordinates) < 3:
        raise HTTPException(400, "Boundary must have at least 3 points")
    
    # Calculate centroid
    def compute_centroid(coords):
        if not coords or len(coords) < 3:
            return None
        x_sum = sum(p[0] for p in coords)
        y_sum = sum(p[1] for p in coords)
        n = len(coords)
        return [x_sum / n, y_sum / n]
    
    centroid = compute_centroid(coordinates)
    
    # Delete existing boundary
    db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.OUTER_BOUNDARY
    ).delete()
    
    # Create new boundary (no directions needed)
    boundary = Polygon(
        project_id=project_id,
        type=PolygonType.OUTER_BOUNDARY,
        name="Outer Boundary",
        coordinates=coordinates,
        centroid=centroid,
    )
    db.add(boundary)
    
    # Update project status
    project.status = ProjectStatus.BOUNDARY_DRAWN
    db.commit()
    db.refresh(boundary)
    
    return {
        "success": True,
        "boundary_id": boundary.id,
        "centroid": centroid
    }

# ============================================================
# ROOM MANAGEMENT
# ============================================================

# ============================================================
# ROOM MANAGEMENT (UPDATED)
# ============================================================

@router.post("/room/{project_id}")
def save_room(
    project_id: int,
    room_data: RoomCreate,
    image_width: float = Query(...),
    image_height: float = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save a room polygon"""

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    boundary = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.OUTER_BOUNDARY
    ).first()

    if not boundary:
        raise HTTPException(400, "Please draw outer boundary first")

    if len(room_data.coordinates) < 3:
        raise HTTPException(400, "Room must have at least 3 points")

    # Keep normalized coordinates for storage
    normalized_coords = normalize_coordinates(
        room_data.coordinates,
        image_width,
        image_height
    )
    direction = room_data.direction

    if direction:
        direction = direction.split("(")[0].strip()
    room = Polygon(
        project_id=project_id,
        parent_id=boundary.id,
        type=PolygonType.ROOM,
        name=room_data.name,
        coordinates=normalized_coords,

        # values supplied by Flutter
        centroid=room_data.centroid,
        direction=direction,
    )

    db.add(room)
    db.commit()
    db.refresh(room)

    from app.models.rule import Rule

    rule = db.query(Rule).filter(
        Rule.entity_type == "room",
        Rule.entity_name == room_data.name,
        Rule.direction_value == direction
    ).first()

    return {
        "success": True,
        "room_id": room.id,
        "centroid": room_data.centroid,
        "direction": room_data.direction,
        "rule": {
            "result": rule.result if rule else "unknown",
            "remedy": rule.remedy_en if rule else None,
            "therapy": rule.therapy if rule else None
        } if rule else None
    }
@router.get("/rooms/{project_id}")
def get_rooms(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get all rooms for a project"""
    
    rooms = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.ROOM
    ).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "coordinates": r.coordinates,
            "centroid": r.centroid,
            "direction": r.direction,
            "color": r.color
        }
        for r in rooms
    ]

@router.delete("/room/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a room"""
    
    room = db.query(Polygon).filter(
        Polygon.id == room_id,
        Polygon.type == PolygonType.ROOM
    ).first()
    
    if not room:
        raise HTTPException(403, "Not authorized")
    
    # Verify ownership through project
    project = db.query(Project).filter(
        Project.id == room.project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(403, "Not authorized")
    
    # Delete associated objects first
    db.query(Polygon).filter(Polygon.parent_id == room_id).delete()
    
    # Delete room
    db.delete(room)
    db.commit()
    
    return {"success": True}

# ============================================================
# OBJECT MANAGEMENT
# ============================================================

@router.post("/object/{project_id}")
def save_object(
    project_id: int,
    object_data: ObjectCreate,  # Use the Pydantic model
    image_width: Optional[float] = Query(None),   # 📍 Changed to Optional so it doesn't break your current URL
    image_height: Optional[float] = Query(None),  # 📍 Changed to Optional so it doesn't break your current URL
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save an object marker"""
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get boundary for verification
    boundary = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.OUTER_BOUNDARY
    ).first()
    
    if not boundary:
        raise HTTPException(400, "Please draw outer boundary first")
    
    # 📍 FIX 1: Directly use the coordinates from the payload. No division!
    normalized_pos = object_data.position 
    direction = object_data.direction
    
    # Find which room contains this point
    containing_room = None
    
    # If room_id is provided, use that room
    if object_data.room_id:
        room_by_id = db.query(Polygon).filter(
            Polygon.id == object_data.room_id,
            Polygon.type == PolygonType.ROOM
        ).first()
        if room_by_id:
            containing_room = room_by_id
    
    # If no room_id provided or room not found, auto-detect by position
    if not containing_room:
        rooms = db.query(Polygon).filter(
            Polygon.project_id == project_id,
            Polygon.type == PolygonType.ROOM
        ).all()
        
        for room in rooms:
            # 📍 This will now work perfectly because normalized_pos isn't broken
            if point_in_polygon(normalized_pos, room.coordinates):
                containing_room = room
                break
    
    # Create object
    obj = Polygon(
        project_id=project_id,
        parent_id=containing_room.id if containing_room else None,
        type=PolygonType.OBJECT,
        name=object_data.object_type,
        coordinates=[normalized_pos],
        centroid=normalized_pos,
        direction=direction,  # 📍 Directly uses the frontend's evaluated direction
        extra_data={"rotation": object_data.rotation}
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    # Update project status
    if project.status == ProjectStatus.BOUNDARY_DRAWN:
        project.status = ProjectStatus.ROOMS_MARKED
        db.commit()
    
    # Get Vastu rule if available
    from app.models.rule import Rule
    rule = db.query(Rule).filter(
        Rule.entity_type == "object",
        Rule.entity_name == object_data.object_type,
        Rule.direction_value == direction
    ).first()
    
    return {
        "success": True,
        "object_id": obj.id,
        "direction": direction,
        "room": containing_room.name if containing_room else None,
        "room_id": containing_room.id if containing_room else None,
        "rotation": object_data.rotation,
        "rule": {
            "result": rule.result if rule else "unknown",
            "remedy": rule.remedy_en if rule else None
        } if rule else None
    }

@router.get("/objects/{project_id}")
def get_objects(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get all objects for a project"""
    
    objects = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.OBJECT
    ).all()
    
    return [
        {
            "id": o.id,
            "type": o.name,
            "position": o.centroid,
            "direction": o.direction,
            "room_id": o.parent_id,
            "rotation": o.extra_data.get("rotation", 0) if o.extra_data else 0
        }
        for o in objects
    ]

@router.delete("/object/{object_id}")
def delete_object(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an object"""
    
    obj = db.query(Polygon).filter(
        Polygon.id == object_id,
        Polygon.type == PolygonType.OBJECT
    ).first()
    
    if not obj:
        raise HTTPException(404, "Object not found")
    
    # Verify ownership
    project = db.query(Project).filter(
        Project.id == obj.project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(403, "Not authorized")
    
    db.delete(obj)
    db.commit()
    
    return {"success": True}

# ============================================================
# COMPLETE PROJECT STATE
# ============================================================

@router.get("/state/{project_id}")
def get_project_state(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get image
    image = db.query(ProjectImage).filter(
        ProjectImage.project_id == project_id
    ).first()
    
    # Get canvas state
    canvas_state = db.query(CanvasState).filter(
        CanvasState.project_id == project_id
    ).first()
    
    # Get boundary (no directions needed)
    boundary = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.OUTER_BOUNDARY
    ).first()
    
    # Get rooms
    rooms = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.ROOM
    ).all()
    
    # Get objects
    objects = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.OBJECT
    ).all()
    
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "starting_degree": float(project.starting_degree),
            "status": project.status
        },
        "image": {
            "url": image.image_path if image else None,
            "has_image": image is not None
        } if image else None,
        "canvas_state": {
            "zoom": float(canvas_state.zoom) if canvas_state else 1.0,
            "pan_x": float(canvas_state.pan_x) if canvas_state else 0.0,
            "pan_y": float(canvas_state.pan_y) if canvas_state else 0.0,
            "rotation": float(canvas_state.rotation) if canvas_state else 0.0
        },
        "boundary": {
            "id": boundary.id,
            "coordinates": boundary.coordinates,
            "centroid": boundary.centroid,
        } if boundary else None,
        "rooms": [
            {
                "id": r.id,
                "name": r.name,
                "coordinates": r.coordinates,
                "centroid": r.centroid,
                "direction": r.direction,
                "direction_angle": float(r.direction_angle) if r.direction_angle else 0.0,
                "color": r.color,
            }
            for r in rooms
        ],
        "objects": [
            {
                "id": o.id,
                "type": o.name,
                "position": o.centroid,
                "direction": o.direction,
                "room_id": o.parent_id,
                "rotation": float(o.extra_data.get("rotation", 0)) if o.extra_data else 0
            }
            for o in objects
        ]
    }

# ============================================================
# FINALIZE PROJECT
# ============================================================

@router.post("/complete/{project_id}")
def complete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark project as ready for report generation"""
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Verify at least one room exists
    room_count = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type == PolygonType.ROOM
    ).count()
    
    if room_count == 0:
        raise HTTPException(400, "At least one room is required")
    
    project.status = ProjectStatus.OBJECTS_MARKED
    db.commit()
    
    return {"success": True}