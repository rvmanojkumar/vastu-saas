from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.db.session import SessionLocal
from app.models.rule import Rule
from app.models.direction import Direction
from app.models.translation import Translation
from app.models.language import Language

router = APIRouter(prefix="/rules", tags=["Vastu Rules"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/criticality/{entity_type}/{entity_name}/{direction_value}")
def get_criticality(
    entity_type: str,  # room or object
    entity_name: str,  # Bedroom, Kitchen, Bed, Stove
    direction_value: str,  # NE, SW, N, S, etc.
    direction_system: str = Query("16", regex="^(16|32|CENTER)$"),
    language_code: Optional[str] = "en",
    db: Session = Depends(get_db)
):
    """
    Get criticality level for placing a room/object in a specific direction
    Returns: good/bad/neutral with remedies, colors, therapy
    """
    
    # Get language
    language = db.query(Language).filter(Language.code == language_code).first()
    
    # Find the rule
    rule = db.query(Rule).filter(
        Rule.entity_type == entity_type,
        Rule.entity_name == entity_name,
        Rule.direction_system == direction_system,
        Rule.direction_value == direction_value
    ).first()
    
    if not rule:
        return {
            "success": False,
            "message": f"No rule found for {entity_name} in {direction_value} direction",
            "criticality": "unknown",
            "remedies": [],
            "colors": [],
            "therapy": None
        }
    
    # Prepare response
    response = {
        "success": True,
        "entity_type": rule.entity_type,
        "entity_name": rule.entity_name,
        "direction_system": rule.direction_system,
        "direction_value": rule.direction_value,
        "criticality": rule.result,  # good/bad/neutral
        "title": rule.title,
        "description": rule.description,
        "remedy": rule.remedy,
        "color": rule.color,
        "therapy": rule.therapy
    }
    
    # Apply translations if needed
    if language and language.code != "en" and not language.is_default:
        translations = db.query(Translation).filter(
            Translation.table_name == "rule",
            Translation.record_id == rule.id,
            Translation.language_id == language.id
        ).all()
        
        for trans in translations:
            if trans.field_name in response:
                response[trans.field_name] = trans.value
    
    return response

@router.get("/remedies/{entity_name}/{direction_value}")
def get_remedies(
    entity_name: str,
    direction_value: str,
    direction_system: str = "16",
    db: Session = Depends(get_db)
):
    """Get remedies, colors, and therapy for a specific placement"""
    
    rule = db.query(Rule).filter(
        Rule.entity_name == entity_name,
        Rule.direction_value == direction_value,
        Rule.direction_system == direction_system
    ).first()
    
    if not rule:
        return {
            "remedies": ["Consult Vastu expert for personalized advice"],
            "colors": ["Use colors as per Vastu principles"],
            "therapy": "Vastu balancing recommended"
        }
    
    # Parse remedies if stored as comma-separated or JSON
    remedies_list = rule.remedy.split("|") if rule.remedy and "|" in rule.remedy else [rule.remedy]
    colors_list = rule.color.split(",") if rule.color else []
    
    return {
        "remedies": remedies_list,
        "colors": colors_list,
        "therapy": rule.therapy,
        "criticality": rule.result
    }

@router.get("/by-direction/{direction_value}")
def get_rules_by_direction(
    direction_value: str,
    direction_system: str = "16",
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all Vastu rules for a specific direction"""
    
    query = db.query(Rule).filter(
        Rule.direction_value == direction_value,
        Rule.direction_system == direction_system
    )
    
    if entity_type:
        query = query.filter(Rule.entity_type == entity_type)
    
    rules = query.all()
    
    # Group by result
    good_rules = [r for r in rules if r.result == "good"]
    bad_rules = [r for r in rules if r.result == "bad"]
    neutral_rules = [r for r in rules if r.result == "neutral"]
    
    return {
        "direction": direction_value,
        "system": direction_system,
        "total": len(rules),
        "good_count": len(good_rules),
        "bad_count": len(bad_rules),
        "neutral_count": len(neutral_rules),
        "good_placements": [{"entity": r.entity_name, "title": r.title} for r in good_rules],
        "bad_placements": [{"entity": r.entity_name, "title": r.title, "remedy": r.remedy} for r in bad_rules]
    }

@router.get("/search")
def search_rules(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Search Vastu rules by entity name or direction"""
    
    search = db.query(Rule).filter(
        (Rule.entity_name.ilike(f"%{query}%")) |
        (Rule.direction_value.ilike(f"%{query}%")) |
        (Rule.title.ilike(f"%{query}%"))
    )
    
    if entity_type:
        search = search.filter(Rule.entity_type == entity_type)
    
    rules = search.limit(limit).all()
    
    return rules