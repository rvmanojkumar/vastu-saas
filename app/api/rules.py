from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import SessionLocal
from app.models.rule import Rule

router = APIRouter(prefix="/rules", tags=["Vastu Rules"])

SUPPORTED_LANGS = {"en", "hi", "mr"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize_lang(language_code: Optional[str]) -> str:
    code = (language_code or "en").lower().strip()
    return code if code in SUPPORTED_LANGS else "en"


def _localized(rule: Rule, field: str, language_code: str) -> Optional[str]:
    """Pick description/remedy for lang, falling back to English."""
    value = getattr(rule, f"{field}_{language_code}", None)
    if value:
        return value
    if language_code != "en":
        return getattr(rule, f"{field}_en", None)
    return value


def _rule_summary(rule: Rule, language_code: str = "en") -> dict:
    return {
        "id": rule.id,
        "entity_type": rule.entity_type,
        "entity_name": rule.entity_name,
        "direction_system": rule.direction_system,
        "direction_value": rule.direction_value,
        "result": rule.result,
        "title": rule.title,
        "description": _localized(rule, "description", language_code),
        "remedy": _localized(rule, "remedy", language_code),
        "description_en": rule.description_en,
        "description_hi": rule.description_hi,
        "description_mr": rule.description_mr,
        "remedy_en": rule.remedy_en,
        "remedy_hi": rule.remedy_hi,
        "remedy_mr": rule.remedy_mr,
        "ratings": float(rule.ratings) if rule.ratings is not None else None,
        "color": rule.color,
        "therapy": rule.therapy,
    }


@router.get("/criticality/{entity_type}/{entity_name}/{direction_value}")
def get_criticality(
    entity_type: str,  # room or object
    entity_name: str,  # Bedroom, Kitchen, Bed, Stove
    direction_value: str,  # NE, SW, N, S, etc.
    direction_system: str = Query("16", pattern="^(16|32|CENTER)$"),
    language_code: Optional[str] = "en",
    db: Session = Depends(get_db),
):
    """
    Get criticality level for placing a room/object in a specific direction
    Returns: good/bad/neutral with remedies, colors, therapy
    """
    lang = _normalize_lang(language_code)

    rule = (
        db.query(Rule)
        .filter(
            Rule.entity_type == entity_type,
            Rule.entity_name == entity_name,
            Rule.direction_system == direction_system,
            Rule.direction_value == direction_value,
        )
        .first()
    )

    if not rule:
        return {
            "success": False,
            "message": f"No rule found for {entity_name} in {direction_value} direction",
            "criticality": "unknown",
            "remedies": [],
            "colors": [],
            "therapy": None,
        }

    description = _localized(rule, "description", lang)
    remedy = _localized(rule, "remedy", lang)

    return {
        "success": True,
        "entity_type": rule.entity_type,
        "entity_name": rule.entity_name,
        "direction_system": rule.direction_system,
        "direction_value": rule.direction_value,
        "criticality": rule.result,
        "title": rule.title,
        "description": description,
        "remedy": remedy,
        "color": rule.color,
        "therapy": rule.therapy,
        "language_code": lang,
    }


@router.get("/remedies/{entity_name}/{direction_value}")
def get_remedies(
    entity_name: str,
    direction_value: str,
    direction_system: str = "16",
    language_code: Optional[str] = "en",
    db: Session = Depends(get_db),
):
    """Get remedies, colors, and therapy for a specific placement"""
    lang = _normalize_lang(language_code)

    rule = (
        db.query(Rule)
        .filter(
            Rule.entity_name == entity_name,
            Rule.direction_value == direction_value,
            Rule.direction_system == direction_system,
        )
        .first()
    )

    if not rule:
        return {
            "remedies": ["Consult Vastu expert for personalized advice"],
            "colors": ["Use colors as per Vastu principles"],
            "therapy": "Vastu balancing recommended",
        }

    remedy = _localized(rule, "remedy", lang)
    remedies_list = (
        remedy.split("|") if remedy and "|" in remedy else ([remedy] if remedy else [])
    )
    colors_list = rule.color.split(",") if rule.color else []

    return {
        "remedies": remedies_list,
        "colors": colors_list,
        "therapy": rule.therapy,
        "criticality": rule.result,
        "language_code": lang,
    }


@router.get("/by-direction/{direction_value}")
def get_rules_by_direction(
    direction_value: str,
    direction_system: str = "16",
    entity_type: Optional[str] = None,
    language_code: Optional[str] = "en",
    db: Session = Depends(get_db),
):
    """Get all Vastu rules for a specific direction"""
    lang = _normalize_lang(language_code)

    query = db.query(Rule).filter(
        Rule.direction_value == direction_value,
        Rule.direction_system == direction_system,
    )

    if entity_type:
        query = query.filter(Rule.entity_type == entity_type)

    rules = query.all()

    good_rules = [r for r in rules if (r.result or "").lower() == "good"]
    bad_rules = [r for r in rules if (r.result or "").lower() == "bad"]
    neutral_rules = [r for r in rules if (r.result or "").lower() == "neutral"]

    return {
        "direction": direction_value,
        "system": direction_system,
        "total": len(rules),
        "good_count": len(good_rules),
        "bad_count": len(bad_rules),
        "neutral_count": len(neutral_rules),
        "good_placements": [
            {"entity": r.entity_name, "title": r.title} for r in good_rules
        ],
        "bad_placements": [
            {
                "entity": r.entity_name,
                "title": r.title,
                "remedy": _localized(r, "remedy", lang),
            }
            for r in bad_rules
        ],
        "language_code": lang,
    }


@router.get("/search")
def search_rules(
    query: str,
    entity_type: Optional[str] = None,
    language_code: Optional[str] = "en",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Search Vastu rules by entity name or direction"""
    lang = _normalize_lang(language_code)

    search = db.query(Rule).filter(
        (Rule.entity_name.ilike(f"%{query}%"))
        | (Rule.direction_value.ilike(f"%{query}%"))
        | (Rule.title.ilike(f"%{query}%"))
    )

    if entity_type:
        search = search.filter(Rule.entity_type == entity_type)

    rules = search.limit(limit).all()

    return [_rule_summary(r, lang) for r in rules]
