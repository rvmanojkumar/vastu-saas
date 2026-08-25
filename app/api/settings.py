from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import get_current_admin
from app.models.user import User
from app.services.settings import (
    admin_settings_view,
    public_firebase_config,
    upsert,
)
from app.services.emailer import send_email, _wrap_html

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SettingsUpdate(BaseModel):
    gmail_user: Optional[str] = None
    gmail_app_password: Optional[str] = None
    firebase_api_key: Optional[str] = None
    firebase_auth_domain: Optional[str] = None
    firebase_project_id: Optional[str] = None
    firebase_storage_bucket: Optional[str] = None
    firebase_messaging_sender_id: Optional[str] = None
    firebase_app_id: Optional[str] = None
    firebase_service_account_json: Optional[str] = None


@router.get("/public")
def get_public_settings(db: Session = Depends(get_db)):
    """Firebase web config for the login/forgot-password screens (no secrets)."""
    return public_firebase_config(db)


@router.get("/admin")
def get_admin_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return admin_settings_view(db)


@router.put("/admin")
def update_admin_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    data = body.dict(exclude_unset=True)
    for key, value in data.items():
        if value is None:
            continue
        upsert(db, key, str(value).strip(), is_secret=key in {"gmail_app_password", "firebase_service_account_json"})
    db.commit()
    return {"message": "Settings saved", **admin_settings_view(db)}


@router.post("/admin/test-email")
def test_email(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    to_email = current_admin.email
    ok = send_email(
        to_email,
        "Spiritual Hut — test email",
        _wrap_html(
            "Test email",
            f"<p>Hello {current_admin.name or 'Admin'},</p><p>Gmail is configured correctly. This is a test message from Vastu SaaS.</p>",
        ),
    )
    if not ok:
        raise HTTPException(400, "Could not send test email. Check Gmail ID and App Password.")
    return {"message": f"Test email sent to {to_email}"}
