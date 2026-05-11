from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.object import Object
from app.models.polygon import Polygon
from app.models.report import Report
from app.core.security import get_current_user
from app.models.user import User
from app.models.subscription import Subscription
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["Projects"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_project(
    data: dict, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ADD THIS
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
    
    # Ensure user_id matches current user
    project = Project(
        user_id=current_user.id,  # Use current_user.id instead of data["user_id"]
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
    
    return project

@router.get("/user/{user_id}")
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    """Get all projects for a user"""
    
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    
    # Get additional info for each project
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
            "created_at": project.created_at if hasattr(project, 'created_at') else None
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