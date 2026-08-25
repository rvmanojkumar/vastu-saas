import json
import logging
import re
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials
from sqlalchemy.orm import Session

from app.services.settings import get_raw

logger = logging.getLogger(__name__)

_APP_NAME = "vastu-saas"


def normalize_phone(phone: Optional[str]) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    if (phone or "").strip().startswith("+"):
        return f"+{digits}"
    return f"+{digits}"


def phones_match(stored: Optional[str], firebase_phone: Optional[str]) -> bool:
    return normalize_phone(stored) == normalize_phone(firebase_phone)


def _load_app(db: Session):
    raw = get_raw(db, "firebase_service_account_json")
    if not raw:
        raise RuntimeError("Firebase service account is not configured")
    info = json.loads(raw)
    cred = credentials.Certificate(info)
    try:
        return firebase_admin.get_app(_APP_NAME)
    except ValueError:
        return firebase_admin.initialize_app(cred, name=_APP_NAME)


def firebase_verification_required(db: Session) -> bool:
    from app.services.settings import public_firebase_config

    cfg = public_firebase_config(db)
    return bool(cfg.get("firebase_ready") and get_raw(db, "firebase_service_account_json"))


def verify_id_token(db: Session, id_token: str) -> dict:
    if not id_token:
        raise ValueError("Missing Firebase ID token")
    app = _load_app(db)
    return auth.verify_id_token(id_token, app=app)


def phone_from_id_token(db: Session, id_token: str) -> str:
    decoded = verify_id_token(db, id_token)
    firebase_phone = decoded.get("phone_number")
    if not firebase_phone:
        raise ValueError("Phone number missing from verification")
    return firebase_phone


def token_matches_phone(db: Session, id_token: str, stored_phone: Optional[str]) -> bool:
    return phones_match(stored_phone, phone_from_id_token(db, id_token))
