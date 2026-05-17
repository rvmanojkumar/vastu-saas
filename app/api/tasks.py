import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.session import SessionLocal
from app.models.task import Task
from app.models.user import User
from app.core.security import get_current_user
from app.models.project import Project

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])

# ============================================================
# PYDANTIC MODELS
# ============================================================

class TaskStatusResponse(BaseModel):
    success: bool
    task_id: str
    status: str
    progress: float
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    project_id: Optional[int] = None

class TaskListResponse(BaseModel):
    success: bool
    total: int
    tasks: List[dict]

class TaskStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(PENDING|PROCESSING|COMPLETED|FAILED)$")
    progress: float = Field(..., ge=0, le=100)
    result_path: Optional[str] = None
    error: Optional[str] = None

# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# TASK STATUS ENDPOINTS
# ============================================================

@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get task status with user validation.
    
    - Validates that the task belongs to the authenticated user
    - Returns detailed task information including progress and result
    """
    
    logger.info(f"User {current_user.id} requesting status for task {task_id}")
    
    # Get task from database
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )
    
    # Validate task ownership
    if task.user_id != current_user.id:
        # Check if user is admin (optional)
        is_admin = getattr(current_user, 'is_admin', False)
        if not is_admin:
            logger.warning(f"User {current_user.id} attempted to access task {task_id} owned by user {task.user_id}")
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this task"
            )
    
    # Get project info if needed
    project = db.query(Project).filter(Project.id == task.project_id).first()
    
    return TaskStatusResponse(
        success=True,
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        result=task.result_path,
        error=getattr(task, 'error', None),
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
        project_id=task.project_id
    )


@router.get("/project/{project_id}/tasks")
def get_project_tasks(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(PENDING|PROCESSING|COMPLETED|FAILED)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all tasks for a specific project with pagination and filtering.
    """
    
    logger.info(f"User {current_user.id} requesting tasks for project {project_id}")
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found or you don't have access"
        )
    
    # Build query
    query = db.query(Task).filter(Task.project_id == project_id)
    
    # Apply status filter if provided
    if status:
        query = query.filter(Task.status == status)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "tasks": [
            {
                "task_id": t.task_id,
                "status": t.status,
                "progress": t.progress,
                "result_path": t.result_path,
                "error": getattr(t, 'error', None),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in tasks
        ]
    }


@router.get("/user/me/tasks")
def get_my_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(PENDING|PROCESSING|COMPLETED|FAILED)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all tasks for the authenticated user with pagination.
    """
    
    logger.info(f"User {current_user.id} requesting their tasks")
    
    # Build query
    query = db.query(Task).filter(Task.user_id == current_user.id)
    
    # Apply status filter if provided
    if status:
        query = query.filter(Task.status == status)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "tasks": [
            {
                "task_id": t.task_id,
                "project_id": t.project_id,
                "status": t.status,
                "progress": t.progress,
                "result_path": t.result_path,
                "error": getattr(t, 'error', None),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in tasks
        ]
    }


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a task (only if it's completed or failed).
    """
    
    logger.info(f"User {current_user.id} requesting to delete task {task_id}")
    
    # Get task
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate ownership
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    
    # Only allow deletion of completed or failed tasks
    if task.status not in ["COMPLETED", "FAILED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete task with status '{task.status}'. Only completed or failed tasks can be deleted."
        )
    
    # Delete task
    db.delete(task)
    db.commit()
    
    logger.info(f"Task {task_id} deleted successfully by user {current_user.id}")
    
    return {
        "success": True,
        "message": f"Task {task_id} deleted successfully"
    }


# ============================================================
# ADMIN ENDPOINTS (Optional, for super users)
# ============================================================

@router.get("/admin/all")
def get_all_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint to get all tasks across all users.
    """
    
    # Check if user is admin
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    tasks = db.query(Task).order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(Task).count()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "tasks": [
            {
                "task_id": t.task_id,
                "user_id": t.user_id,
                "project_id": t.project_id,
                "status": t.status,
                "progress": t.progress,
                "result_path": t.result_path,
                "error": getattr(t, 'error', None),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in tasks
        ]
    }


# ============================================================
# TASK STATISTICS
# ============================================================

@router.get("/stats/me")
def get_my_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get task statistics for the authenticated user.
    """
    
    tasks = db.query(Task).filter(Task.user_id == current_user.id).all()
    
    stats = {
        "total": len(tasks),
        "pending": sum(1 for t in tasks if t.status == "PENDING"),
        "processing": sum(1 for t in tasks if t.status == "PROCESSING"),
        "completed": sum(1 for t in tasks if t.status == "COMPLETED"),
        "failed": sum(1 for t in tasks if t.status == "FAILED"),
    }
    
    return {
        "success": True,
        "stats": stats
    }