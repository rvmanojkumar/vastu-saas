from typing import List, Dict, Any
from app.api import rules
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

# def compute_vastu_analysis(db, project_id: int):

#     from app.models import Polygon, Rule

#     # =========================
#     # FETCH DATA
#     # =========================
#     polygons = db.query(Polygon).filter(
#         Polygon.project_id == project_id,
#         Polygon.type.in_(["room", "object"])
#     ).all()

#     rules = load_rules(db)

#     rows = []
#     total = 0

#     for poly in polygons:

#         direction = normalize_direction(poly.direction)

#         matched = None

#         for rule in rules:
#             if (
#                 rule["entity_type"] == poly.type and
#                 rule["entity_name"] == poly.name and
#                 rule["direction_value"] == direction
#             ):
#                 matched = rule
#                 break

#         if matched:
#             rating = matched["ratings"]
#             analysis = matched["description"]
#             remedy = matched["remedy"]
#             color = matched["color"]
#             state = matched["result"]
#         else:
#             rating = 0
#             analysis = "No rule found"
#             remedy = "Manual review required"
#             color = "#ccc"
#             state = "neutral"

#         rows.append({
#             "name": poly.name,
#             "direction": direction,
#             "rating": rating,
#             "analysis": analysis,
#             "remedy": remedy,
#             "color": color,
#             "state": state
#         })

#         total += rating

#     overall = round(total / len(polygons), 2) if polygons else 0

#     return {
#         "overall": overall,
#         "rows": rows
#     }

# def load_rules(db):

#     cached = get_cached_rules()
#     if cached:
#         return cached

#     rules = db.query(Rule).all()

#     serialized = [
#         {
#             "entity_type": r.entity_type,
#             "entity_name": r.entity_name,
#             "direction_system": r.direction_system,
#             "direction_value": r.direction_value,
#             "ratings": r.ratings,
#             "description": r.description,
#             "remedy": r.remedy,
#             "color": r.color,
#             "result": r.result
#         }
#         for r in rules
#     ]

#     set_cached_rules(serialized)
#     return serialized
def load_rules(db):
    print("NEW LOAD_RULES RUNNING")
    # cached = get_cached_rules()

    # if False and cached:
    #     return cached

    # # Only accept the new dictionary format
    # if cached and isinstance(cached, dict):
    #     return cached
    print("REBUILDING RULE CACHE")
    rules = db.query(Rule).all()

    lookup = {}

    for r in rules:
        key = cache_key(
            r.entity_type,
            r.entity_name,
            r.direction_system,
            r.direction_value
)
        lookup[key] = {
            "title": r.title,
            "description": r.description,
            "remedy": r.remedy,
            "therapy": r.therapy,
            "ratings": float(r.ratings or 0),
            "color": r.color,
            "result": r.result,
        }

    set_cached_rules(lookup)

    return lookup

def compute_vastu_analysis(
    db,
    project_id: int,
    direction_system: str = "16"
):
    from app.models import Polygon

    # =========================
    # FETCH DATA
    # =========================
    polygons = (
        db.query(Polygon)
        .filter(
            Polygon.project_id == project_id,
            Polygon.type.in_(["room", "object"])
        )
        .all()
    )

    rules = load_rules(db)
    rows = []
    total = 0.0
    count =0
    for poly in polygons:

        direction = normalize_direction(poly.direction)

        rule_key = cache_key(
            poly.type,
            poly.name,
            direction_system,
            direction
        )

        matched = rules.get(rule_key)

        if matched:
            rating = float(matched.get("ratings", 0))
            analysis = matched.get("description") or ""
            remedy = matched.get("remedy") or ""
            therapy = matched.get("therapy") or ""
            title = matched.get("title") or ""
            color = matched.get("color") or "#ccc"
            state = matched.get("result") or "neutral"
        else:
            rating = 0
            title = ""
            analysis = "No rule found"
            remedy = "Manual review required"
            therapy = ""
            color = "#ccc"
            state = "neutral"

        rows.append({
            "name": poly.name,
            "type": poly.type,
            "direction": direction,

            "title": title,
            "analysis": analysis,
            "remedy": remedy,
            "therapy": therapy,

            "rating": rating,
            "color": color,
            "status": state,
        })
        if(rating): 
            total += rating
            count += 1
    overall = round(total / count, 2) if count > 0 else 0

    return {
        "overall": overall,
        "rows": rows
    }
def cache_key(entity_type, entity_name, system, direction):
    return (
        f"{(entity_type or '').strip().lower()}|"
        f"{(entity_name or '').strip().lower()}|"
        f"{(system or '').strip().lower()}|"
        f"{(direction or '').strip().lower()}"
    )