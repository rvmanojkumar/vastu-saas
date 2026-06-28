from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.session import SessionLocal
from app.models.user import User
from app.models.subscription import Subscription
from app.core.security import (
    hash_password as get_password_hash,
    create_refresh_token, get_current_user,
    verify_password,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user

)
class RefreshTokenRequest(BaseModel):
    refresh_token: str

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: Optional[str] = "user"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str
    role: str

class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    is_active: bool
    plan_id: Optional[int]
    reports_limit: Optional[int]
    reports_used: Optional[int]
    remaining_reports: Optional[int]
    expires_on: Optional[datetime]
    can_create_project: bool
    can_generate_report: bool
    message: str
    whitelabel:bool

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(400, "Email already registered")
    
    # Check if phone exists
    existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_phone:
        raise HTTPException(400, "Phone number already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        password=hashed_password,
        role=user_data.role,
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access tokens
    access_token = create_access_token(data={"sub": new_user.id})
    refresh_token = create_refresh_token(data={"sub": new_user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role
    )

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return tokens"""
    
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role
    )

@router.post("/refresh")
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "refresh":
            raise HTTPException(401, "Invalid refresh token")

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(401, "User not found or inactive")

        new_access_token = create_access_token(data={"sub": user.id})
        new_refresh_token = create_refresh_token(data={"sub": user.id})  # rotate refresh token too

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,  # Flutter should store this new one
            "token_type": "bearer"
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token has expired, please login again")
    except:
        raise HTTPException(401, "Invalid refresh token")
@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current logged-in user information"""
    
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "logo": current_user.logo,
        "header_title": current_user.header_title,
        "header_subtitle": current_user.header_subtitle,
        "address": current_user.address,
        "footer_text": current_user.footer_text,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }

@router.get("/subscription-status")
def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check user's subscription status and available reports"""
    
    # Get active subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active",
        Subscription.end_date > datetime.utcnow()
    ).first()
    whitelabel_status = subscription.plan.is_whitelabel if subscription and subscription.plan else False
    if not subscription:
        return SubscriptionStatusResponse(
            has_subscription=False,
            is_active=False,
            plan_id=None,
            reports_limit=None,
            reports_used=None,
            remaining_reports=None,
            expires_on=None,
            can_create_project=False,
            can_generate_report=False,
            message="No active subscription. Please purchase a plan to create projects and generate reports.",
            is_whitelabel=whitelabel_status
            
        )
    
    remaining = subscription.reports_limit - subscription.reports_used
    
    # Check if can create project (always true if subscription active)
    can_create = subscription.status == "active" and subscription.end_date > datetime.utcnow()
    
    # Check if can generate report (need remaining reports > 0)
    can_generate = remaining > 0
    
    message = f"You have {remaining} reports remaining out of {subscription.reports_limit}"
    if remaining <= 0:
        message = "You have exhausted your report limit. Please upgrade your plan."
    elif remaining <= 3:
        message = f"Warning: Only {remaining} reports remaining. Consider upgrading."
    whitelabel_status = subscription.plan.is_whitelabel if subscription and subscription.plan else False
    return SubscriptionStatusResponse(
        has_subscription=True,
        is_active=True,
        plan_id=subscription.plan_id,
        reports_limit=subscription.reports_limit,
        reports_used=subscription.reports_used,
        remaining_reports=remaining,
        expires_on=subscription.end_date,
        can_create_project=can_create,
        can_generate_report=can_generate,
        message=message,
        whitelabel=whitelabel_status,
    )

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)"""
    # In a stateless JWT system, we don't need server-side logout
    # Client should remove tokens from storage
    return {"message": "Logged out successfully"}