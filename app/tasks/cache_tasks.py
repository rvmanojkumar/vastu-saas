from app.core.celery_app import celery
from app.db.session import SessionLocal
from app.models.rule import Rule
from app.core.cache import set_cached_rooms, set_cached_objects


@celery.task
def sync_dropdown_cache():
    db = SessionLocal()

    try:
        # -------- ROOMS --------
        rooms = (
            db.query(Rule.entity_name)
            .filter(Rule.entity_type == "room")
            .distinct()
            .order_by(Rule.entity_name)
            .all()
        )

        room_list = [r[0] for r in rooms if r[0]]
        set_cached_rooms(room_list)

        # -------- OBJECTS --------
        objects = (
            db.query(Rule.entity_name)
            .filter(Rule.entity_type == "object")
            .distinct()
            .order_by(Rule.entity_name)
            .all()
        )

        object_list = [r[0] for r in objects if r[0]]
        set_cached_objects(object_list)

        return {
            "status": "success",
            "rooms": len(room_list),
            "objects": len(object_list)
        }

    finally:
        db.close()