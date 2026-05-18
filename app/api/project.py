from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.models.project import Project,ProjectStatus
from app.models.object import Object
from app.models.polygon import Polygon
from app.models.report import Report
from app.core.security import get_current_user
from app.models.user import User
from app.models.subscription import Subscription
from app.models.floorplan import ProjectImage,CanvasState
from datetime import datetime
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