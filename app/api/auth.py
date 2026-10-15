import re
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from jose import jwt
from app.db.session import SessionLocal
from app.models.user import User
from app.models.subscription import Subscription
from app.services.subscription import get_active_subscription
from app.core.security import (
    hash_password as get_password_hash,
    verify_password,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
)
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=72)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: Optional[str] = "user"
    firebase_id_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    firebase_id_token: str
    new_password: str = Field(..., min_length=6, max_length=72)

class VerifyPhoneRequest(BaseModel):
    firebase_id_token: str

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
    has_subscription: bool = False

class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    is_active: bool
    plan_id: Optional[int]
    product_access: Optional[str] = None
    reports_limit: Optional[int]
    reports_used: Optional[int]
    remaining_reports: Optional[int]
    vastu_reports_limit: Optional[int] = None
    vastu_reports_used: Optional[int] = None
    numerology_reports_limit: Optional[int] = None
    numerology_reports_used: Optional[int] = None
    expires_on: Optional[datetime]
    can_create_project: bool
    can_generate_report: bool
    message: str
    whitelabel: bool = False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _has_active_plan(db: Session, user_id: int) -> bool:
    sub = get_active_subscription(db, user_id)
    if not sub:
        return False
    if sub.end_date and sub.end_date < datetime.utcnow():
        return False
    return True


def _token_response(user: User, db: Session) -> TokenResponse:
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        has_subscription=_has_active_plan(db, user.id),
    )

def _valid_mobile(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return len(digits) == 10 and digits[:1] in "6789"


def _assert_otp_matches_phone(db: Session, id_token: str, phone: str) -> None:
    from app.services.firebase_auth import token_matches_phone

    try:
        ok = token_matches_phone(db, id_token, phone)
    except Exception:
        raise HTTPException(400, "Invalid or expired OTP. Please request a new OTP.")
    if not ok:
        raise HTTPException(400, "OTP does not match this phone number")


def _resume_unpaid_user(user: User, password: str, db: Session) -> TokenResponse:
    """Log an unpaid account back in so they can complete payment."""
    if not verify_password(password, user.password):
        raise HTTPException(
            400,
            "This account is already registered. Log in to complete payment.",
        )
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return _token_response(user, db)


@router.post("/register", response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user, or resume an unpaid signup with the same credentials."""

    if not _valid_mobile(user_data.phone):
        raise HTTPException(400, "Enter a valid 10-digit mobile number")

    existing_email = db.query(User).filter(User.email == user_data.email).first()
    existing_phone = db.query(User).filter(User.phone == user_data.phone).first()

    if existing_email and existing_phone and existing_email.id != existing_phone.id:
        raise HTTPException(400, "Email already registered")

    existing = existing_email or existing_phone
    if existing:
        if existing.role == "admin" or _has_active_plan(db, existing.id):
            if existing_email:
                raise HTTPException(400, "Email already registered")
            raise HTTPException(400, "Phone number already registered")
        if user_data.firebase_id_token:
            _assert_otp_matches_phone(db, user_data.firebase_id_token, existing.phone)
            existing.phone_verified = True
        return _resume_unpaid_user(existing, user_data.password, db)

    phone_verified = False
    if user_data.firebase_id_token:
        _assert_otp_matches_phone(db, user_data.firebase_id_token, user_data.phone)
        phone_verified = True

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        password=hashed_password,
        role=user_data.role,
        phone_verified=phone_verified,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    try:
        from app.services.emailer import send_registration_email
        send_registration_email(new_user.name, new_user.email)
    except Exception:
        pass

    return _token_response(new_user, db)

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return tokens"""

    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _token_response(user, db)

@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password after Firebase phone OTP verification."""
    from app.services.firebase_auth import phones_match, verify_id_token

    try:
        decoded = verify_id_token(db, body.firebase_id_token)
    except Exception:
        raise HTTPException(400, "Invalid or expired OTP session. Please request a new OTP.")

    firebase_phone = decoded.get("phone_number")
    if not firebase_phone:
        raise HTTPException(400, "Phone number missing from verification")

    last10 = re.sub(r"\D", "", firebase_phone)[-10:]
    if len(last10) < 10:
        raise HTTPException(400, "Invalid phone number on OTP session")

    candidates = (
        db.query(User)
        .filter(User.is_active == True, User.phone.like(f"%{last10}"))
        .all()
    )
    user = next((u for u in candidates if phones_match(u.phone, firebase_phone)), None)
    if not user:
        raise HTTPException(400, "No account found for this phone number")

    user.password = get_password_hash(body.new_password)
    db.commit()
    return {"message": "Password updated. You can now log in."}

@router.post("/verify-phone")
def verify_phone(
    body: VerifyPhoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark the logged-in user's phone as verified after Firebase OTP."""
    _assert_otp_matches_phone(db, body.firebase_id_token, current_user.phone)
    current_user.phone_verified = True
    db.commit()
    return {"message": "Phone number verified", "phone_verified": True}

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
        "phone_verified": bool(current_user.phone_verified),
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
    product: str = Query("vastu", description="vastu | numerology"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check user's subscription status and available reports for a product."""
    product = (product or "vastu").lower()
    if product not in ("vastu", "numerology"):
        raise HTTPException(400, "product must be vastu or numerology")

    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active",
        Subscription.end_date > datetime.utcnow()
    ).first()

    empty = SubscriptionStatusResponse(
        has_subscription=False,
        is_active=False,
        plan_id=None,
        product_access=None,
        reports_limit=None,
        reports_used=None,
        remaining_reports=None,
        vastu_reports_limit=None,
        vastu_reports_used=None,
        numerology_reports_limit=None,
        numerology_reports_used=None,
        expires_on=None,
        can_create_project=False,
        can_generate_report=False,
        message="No active subscription. Please purchase a plan to create projects and generate reports.",
        whitelabel=False,
    )

    if not subscription:
        return empty

    access = (subscription.product_access or "both").lower()
    whitelabel_status = bool(
        subscription.plan.is_whitelabel if subscription.plan else False
    )

    if product == "numerology":
        limit = subscription.numerology_reports_limit or 0
        used = subscription.numerology_reports_used or 0
    else:
        limit = subscription.vastu_reports_limit or subscription.reports_limit or 0
        used = subscription.vastu_reports_used
        if used is None:
            used = subscription.reports_used or 0

    remaining = max(limit - used, 0)
    product_allowed = access in ("both", product)
    can_create = True
    can_generate = product_allowed and remaining > 0

    if not product_allowed:
        message = f"Your plan ({access}) does not include {product} reports."
    elif remaining <= 0:
        message = f"You have exhausted your {product} report limit. Please upgrade your plan."
    elif remaining <= 3:
        message = f"Warning: Only {remaining} {product} reports remaining. Consider upgrading."
    else:
        message = f"You have {remaining} {product} reports remaining out of {limit}"

    return SubscriptionStatusResponse(
        has_subscription=True,
        is_active=True,
        plan_id=subscription.plan_id,
        product_access=access,
        reports_limit=limit,
        reports_used=used,
        remaining_reports=remaining,
        vastu_reports_limit=subscription.vastu_reports_limit,
        vastu_reports_used=subscription.vastu_reports_used,
        numerology_reports_limit=subscription.numerology_reports_limit,
        numerology_reports_used=subscription.numerology_reports_used,
        expires_on=subscription.end_date,
        can_create_project=can_create,
        can_generate_report=can_generate,
        message=message,
        whitelabel=whitelabel_status,
    )

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Let a logged-in user change their own password."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.current_password, user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password",
        )

    user.password = get_password_hash(data.new_password)
    db.commit()
    return {"success": True, "message": "Password updated successfully"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)"""
    # In a stateless JWT system, we don't need server-side logout
    # Client should remove tokens from storage
    return {"message": "Logged out successfully"}