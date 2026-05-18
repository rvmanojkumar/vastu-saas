from typing import List, Dict, Any
from app.models import Polygon, Rule
from app.core.cache import get_cached_rules, set_cached_rules
from app.utils.direction import normalize_direction


# =========================
# NORMALIZE HELPERS
# =========================
def normalize(val: str) -> str:
    return (val or "").strip().lower()


# =========================
# FIND MATCHING RULE
# =========================
def find_rule(rules: List[Rule], entity_type: str, entity_name: str, direction: str, system: str = "16"):
    """
    Match polygon with rule table
    """

    entity_type = normalize(entity_type)
    entity_name = normalize(entity_name)
    direction = normalize(direction)

    for rule in rules:

        if normalize(rule.entity_type) != entity_type:
            continue

        if normalize(rule.entity_name) != entity_name:
            continue

        if normalize(rule.direction_system) != system:
            continue

        if normalize(rule.direction_value) != direction:
            continue

        return rule

    return None

def compute_vastu_analysis(db, project_id: int):

    from app.models import Polygon, Rule

    # =========================
    # FETCH DATA
    # =========================
    polygons = db.query(Polygon).filter(
        Polygon.project_id == project_id,
        Polygon.type.in_(["room", "object"])
    ).all()

    rules = load_rules(db)

    rows = []
    total = 0

    for poly in polygons:

        direction = normalize_direction(poly.direction)

        matched = None

        for rule in rules:
            if (
                rule["entity_type"] == poly.type and
                rule["entity_name"] == poly.name and
                rule["direction_value"] == direction
            ):
                matched = rule
                break

        if matched:
            rating = matched["ratings"]
            analysis = matched["description"]
            remedy = matched["remedy"]
            color = matched["color"]
            state = matched["result"]
        else:
            rating = 0
            analysis = "No rule found"
            remedy = "Manual review required"
            color = "#ccc"
            state = "neutral"

        rows.append({
            "name": poly.name,
            "direction": direction,
            "rating": rating,
            "analysis": analysis,
            "remedy": remedy,
            "color": color,
            "state": state
        })

        total += rating

    overall = round(total / len(polygons), 2) if polygons else 0

    return {
        "overall": overall,
        "rows": rows
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