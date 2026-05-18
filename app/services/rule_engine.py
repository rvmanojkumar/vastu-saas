from typing import List, Dict, Any
from app.models import Polygon, Rule
from app.core.cache import get_cached_rules, set_cached_rules
from app.utils.direction import normalize_direction
from sqlalchemy.orm import Session


def evaluate_rule(db: Session, entity_type, entity_name, direction_system, direction_value):
    """
    Fetch matching rule from DB
    """

    rule = db.query(Rule).filter(
        Rule.entity_type == entity_type,
        Rule.entity_name == entity_name,
        Rule.direction_system == direction_system,
        Rule.direction_value == direction_value
    ).first()

    if not rule:
        return {
            "result": "neutral",
            "title": "No Rule Defined",
            "description": "No vastu rule defined for this combination",
            "remedy": None
        }

    return {
        "result": rule.result,
        "title": rule.title,
        "description": rule.description,
        "remedy": rule.remedy
    }
def load_rules(db):

    cached = get_cached_rules()
    if cached:
        return cached

    rules = db.query(Rule).all()

    serialized = [
        {
            "entity_type": r.entity_type,
            "entity_name": r.entity_name,
            "direction_system": r.direction_system,
            "direction_value": r.direction_value,
            "ratings": r.ratings,
            "description": r.description,
            "remedy": r.remedy,
            "color": r.color,
            "result": r.result
        }
        for r in rules
    ]

    set_cached_rules(serialized)
    return serialized