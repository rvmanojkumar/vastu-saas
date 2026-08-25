import logging
from base64 import urlsafe_b64encode
from datetime import datetime
from hashlib import sha256
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.security import SECRET_KEY
from app.models.system_setting import SystemSetting

logger = logging.getLogger(__name__)

PUBLIC_FIREBASE_KEYS = (
    "firebase_api_key",
    "firebase_auth_domain",
    "firebase_project_id",
    "firebase_storage_bucket",
    "firebase_messaging_sender_id",
    "firebase_app_id",
)

SECRET_KEYS = frozenset({"gmail_app_password", "firebase_service_account_json"})

ALL_KEYS = (
    "gmail_user",
    "gmail_app_password",
    *PUBLIC_FIREBASE_KEYS,
    "firebase_service_account_json",
)


def _fernet() -> Fernet:
    digest = sha256((SECRET_KEY or "vastu-settings").encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


def encrypt_value(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        logger.warning("Could not decrypt a system setting; value may be stale")
        return ""


def get_raw(db: Session, key: str) -> Optional[str]:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row or row.value is None or row.value == "":
        return None
    if row.is_secret:
        return decrypt_value(row.value)
    return row.value


def is_set(db: Session, key: str) -> bool:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return bool(row and row.value)


def upsert(db: Session, key: str, value: Optional[str], is_secret: bool) -> None:
    if value is None:
        return
    stored = encrypt_value(value) if is_secret and value else value
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        if is_secret and value == "":
            return
        row.value = stored
        row.is_secret = is_secret
        row.updated_at = datetime.utcnow()
    else:
        if is_secret and value == "":
            return
        db.add(
            SystemSetting(
                key=key,
                value=stored,
                is_secret=is_secret,
                updated_at=datetime.utcnow(),
            )
        )


def public_firebase_config(db: Session) -> dict:
    data = {key: get_raw(db, key) or "" for key in PUBLIC_FIREBASE_KEYS}
    ready = bool(data.get("firebase_api_key") and data.get("firebase_project_id") and data.get("firebase_app_id"))
    return {"firebase_ready": ready, **data}


def admin_settings_view(db: Session) -> dict:
    view = {
        "gmail_user": get_raw(db, "gmail_user") or "",
        "gmail_app_password_set": is_set(db, "gmail_app_password"),
        "firebase_service_account_set": is_set(db, "firebase_service_account_json"),
    }
    for key in PUBLIC_FIREBASE_KEYS:
        view[key] = get_raw(db, key) or ""
    return view
