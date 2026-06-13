import re
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

def load_rules(db):
    print("NEW LOAD_RULES RUNNING")
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

def compute_vastu_analysis(db, project_id: int):
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
    count = 0
    
    for poly in polygons:
        # 1. Normalize the direction string
        direction = normalize_direction(poly.direction)

        # 2. DYNAMIC SYSTEM DETECTION
        # If direction matches patterns like E1, S3, N8 (Letter + Number), it's a 32-system.
        # Otherwise, default it to the 16-system.
        if re.match(r'^[A-Za-z]+\d+$', direction.strip()):
            determined_system = "32"
        else:
            determined_system = "16"

        # 3. Generate the cache key using the dynamically found system
        rule_key = cache_key(
            poly.type,
            poly.name,
            determined_system,
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
            "system_used": determined_system, # Added for easier UI debugging!

            "title": title,
            "analysis": analysis,
            "remedy": remedy,
            "therapy": therapy,

            "rating": rating,
            "color": color,
            "status": state,
        })
        if rating: 
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