from sqlalchemy.orm import Session
from app.models.rule import Rule


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