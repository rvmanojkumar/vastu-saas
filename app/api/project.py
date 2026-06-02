import os

from fastapi import APIRouter, Depends, HTTPException,File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List
from app import db
from app.db.session import SessionLocal
from app.models.project import Project,ProjectStatus
from app.models.object import Object
from app.models.polygon import Polygon
from app.models.report import Report
from app.core.security import get_current_user
from app.models.user import User
from app.models.rule import Rule
from app.models.subscription import Subscription
from app.models.floorplan import ProjectImage,CanvasState
from datetime import datetime
from app.core.cache import get_cached_rooms, get_cached_objects,set_cached_rooms, set_cached_objects
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("")
def create_project(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Vastu project (requires authentication)"""
    
    # Check subscription status before creating project
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active",
        Subscription.end_date > datetime.utcnow()
    ).first()
    
    if not subscription:
        raise HTTPException(403, "Active subscription required to create projects")
    
    # Create project
    project = Project(
        user_id=current_user.id,
        name=data["name"],
        description=data.get("description", ""),
        image_path=data.get("image_path", ""),
        rotation=data.get("rotation", 0),
        starting_degree=data.get("starting_degree", 0)
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create polygon if provided
    if "polygon" in data:
        polygon = Polygon(
            project_id=project.id,
            coordinates=data["polygon"],
            centroid_x=data.get("centroid_x"),
            centroid_y=data.get("centroid_y")
        )
        db.add(polygon)
        db.commit()
    
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "image_path": project.image_path,
        "rotation": project.rotation,
        "starting_degree": project.starting_degree,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "objects_count": 0,
        "reports_count": 0
    }

@router.get("/my-projects")
def get_my_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get projects for the authenticated user"""
    
    try:
        projects = db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.updated_at.desc()).all()
        
        result = []
        for project in projects:
            objects_count = db.query(Object).filter(Object.project_id == project.id).count()
            reports_count = db.query(Report).filter(Report.project_id == project.id).count()
            
            result.append({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "image_path": project.image_path,
                "rotation": project.rotation,
                "starting_degree": project.starting_degree,
                "objects_count": objects_count,
                "reports_count": reports_count,
                "status": project.status,  # ✅ Make sure this is included
                "created_at": project.created_at.isoformat() if project.created_at else None
            })
        
        return result
    except Exception as e:
        print(f"Error in get_my_projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}")
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    """Get all projects for a specific user (admin only)"""
    
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    
    result = []
    for project in projects:
        objects_count = db.query(Object).filter(Object.project_id == project.id).count()
        reports_count = db.query(Report).filter(Report.project_id == project.id).count()
        
        result.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "image_path": project.image_path,
            "objects_count": objects_count,
            "reports_count": reports_count,
            "created_at": project.created_at.isoformat() if project.created_at else None
        })
    
    return result

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project and all associated data"""
    
    # Delete objects first
    db.query(Object).filter(Object.project_id == project_id).delete()
    
    # Delete polygon
    db.query(Polygon).filter(Polygon.project_id == project_id).delete()
    
    # Delete reports
    db.query(Report).filter(Report.project_id == project_id).delete()
    
    # Delete project
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
        return {"success": True, "message": "Project deleted"}
    
    raise HTTPException(404, "Project not found")
@router.put("/{project_id}/starting-degree")
def update_starting_degree(
    project_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the starting degree (north direction) for a project"""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id, 
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # Update starting degree
    project.starting_degree = data.get('starting_degree', 0)
    db.commit()

    return {"success": True, "starting_degree": project.starting_degree}
@router.delete("/{project_id}/image")
async def delete_floorplan_image(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete floorplan image and all associated data"""
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get the image
    image = db.query(ProjectImage).filter(
        ProjectImage.project_id == project_id
    ).first()
    
    if not image:
        raise HTTPException(404, "Image not found")
    
    # Store file path before deletion
    file_path = image.image_path.lstrip('/') if image.image_path else None
    
    try:
        # Start a transaction
        # Delete all polygons (this will cascade to child objects if relationships exist)
        db.query(Polygon).filter(Polygon.project_id == project_id).delete()
        
        # Delete canvas state
        db.query(CanvasState).filter(CanvasState.project_id == project_id).delete()
        
        # Delete the image record
        db.delete(image)
        
        # Update project status
        project.status = ProjectStatus.UPLOADED  # or DRAFT
        project.starting_degree = 0  # Reset if needed
        project.rotation = 0  # Reset if needed
        
        db.commit()
        
        # Delete physical file after successful database transaction
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            
            # Try to remove parent directory if empty
            dir_path = os.path.dirname(file_path)
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            try:
                os.rmdir(dir_path)
            except OSError:
                pass  # Directory not empty
        
        return {
            "success": True,
            "message": "Image and associated data deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Error deleting image: {str(e)}")
@router.post("/{project_id}/upload-compass")
async def upload_compass_image(
    project_id: int,
    divisions: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    try:
        target_dir = os.path.join("storage/projects", str(project_id))
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        return {
            "success": True,
            "message": "Compass image uploaded successfully",
            "file_path": file_path,
            "divisions": divisions
        }
    except Exception as e:
        logger.error(f"Error uploading compass image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
def reload_rooms_cache(db: Session):
    rooms = (
        db.query(Rule.entity_name)
        .filter(Rule.entity_type == "room")
        .distinct()
        .order_by(Rule.entity_name)
        .all()
    )

    room_list = [r[0] for r in rooms if r[0]]
    set_cached_rooms(room_list)
    return room_list

def reload_objects_cache(db: Session):
    objects = (
        db.query(Rule.entity_name)
        .filter(Rule.entity_type == "object")
        .distinct()
        .order_by(Rule.entity_name)
        .all()
    )

    object_list = [r[0] for r in objects if r[0]]
    set_cached_objects(object_list)
    return object_list

@router.get("/rooms")
def get_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Try to get from cache
    rooms = get_cached_rooms()
    
    # If cache is empty, reload from database
    if rooms is None:
        rooms = reload_rooms_cache(db)
    
    return {
        "success": True,
        "rooms": rooms or []
    }

@router.get("/objects")
def get_objects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Try to get from cache
    objects = get_cached_objects()
    
    # If cache is empty, reload from database
    if objects is None:
        objects = reload_objects_cache(db)
    
    return {
        "success": True,
        "objects": objects or []
    }
@router.delete("/room/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a room"""
    
    room = db.query(Polygon).filter(
        Polygon.id == room_id
    ).first()
    
    if not room:
        raise HTTPException(403, "Not authorized")
    
    # Verify ownership through project
    project = db.query(Project).filter(
        Project.id == room.project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(404, "Not found")
    
    # Delete associated objects first
    db.query(Polygon).filter(Polygon.parent_id == room_id).delete()
    
    # Delete room
    db.delete(room)
    db.commit()
    
    return {"success": True}
@router.delete("/object/{object_id}")
def delete_object(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an object"""
    print("Deleting object:", object_id)
    obj = db.query(Polygon).filter(
        Polygon.id == object_id,
        Polygon.type == 'object'
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

#this should be the last endpoint in this file, do not add any code after this
@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get detailed project information"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    polygon = db.query(Polygon).filter(Polygon.project_id == project_id).first()
    
    return {
        "project": project,
        "objects": objects,
        "polygon": polygon,
        "objects_count": len(objects)
    }
#this should be the last endpoint in this file, do not add any code after this
