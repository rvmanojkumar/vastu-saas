from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import *

from datetime import datetime, timedelta


def seed():
    db: Session = SessionLocal()

    # =====================================================
    # EXISTING SEEDING
    # =====================================================

    # ✅ USER
    existing_user = db.query(User).filter(User.id == 1).first()

    if not existing_user:

        user = User(
            id=1,
            name="Demo User",
            email="demo@test.com",
            phone="9999999999",
            password="hashed"
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    else:
        user = existing_user

    # ✅ PLAN
    existing_plan = db.query(Plan).filter(Plan.id == 1).first()

    if not existing_plan:

        plan = Plan(
            id=1,
            name="Pro Plan",
            price=999,
            duration_days=30,
            report_limit=20,
            is_whitelabel=True
        )

        db.add(plan)
        db.commit()

    # ✅ SUBSCRIPTION
    existing_sub = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).first()

    if not existing_sub:

        sub = Subscription(
            user_id=user.id,
            plan_name="Pro Plan",
            status="active",
            reports_limit=20,
            reports_used=0,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30)
        )

        db.add(sub)
        db.commit()

    # ✅ PROJECT
    existing_project = db.query(Project).filter(
        Project.id == 1
    ).first()

    if not existing_project:

        project = Project(
            id=1,
            user_id=user.id,
            name="Demo Project",
            description="Test",
            image_path=None,
            rotation=0,
            starting_degree=0
        )

        db.add(project)
        db.commit()

    # =====================================================
    # NEW TABLES SEEDING
    # =====================================================

    # =====================================================
    # LANGUAGES
    # =====================================================

    languages = [
        {
            "code": "en",
            "name": "English",
            "is_default": True
        }
    ]

    for item in languages:

        exists = db.query(Language).filter(
            Language.code == item["code"]
        ).first()

        if not exists:
            db.add(Language(**item))

    db.commit()

    # =====================================================
    # DIRECTIONS (16 SYSTEM)
    # =====================================================

    directions = [
        {
            "code": "N",
            "name": "North",
            "degree_start": 348.75,
            "degree_end": 11.25,
            "system_type": "16",
            "sort_order": 1
        },
        {
            "code": "NNE",
            "name": "North North East",
            "degree_start": 11.25,
            "degree_end": 33.75,
            "system_type": "16",
            "sort_order": 2
        },
        {
            "code": "NE",
            "name": "North East",
            "degree_start": 33.75,
            "degree_end": 56.25,
            "system_type": "16",
            "sort_order": 3
        },
        {
            "code": "ENE",
            "name": "East North East",
            "degree_start": 56.25,
            "degree_end": 78.75,
            "system_type": "16",
            "sort_order": 4
        },
        {
            "code": "E",
            "name": "East",
            "degree_start": 78.75,
            "degree_end": 101.25,
            "system_type": "16",
            "sort_order": 5
        },
        {
            "code": "ESE",
            "name": "East South East",
            "degree_start": 101.25,
            "degree_end": 123.75,
            "system_type": "16",
            "sort_order": 6
        },
        {
            "code": "SE",
            "name": "South East",
            "degree_start": 123.75,
            "degree_end": 146.25,
            "system_type": "16",
            "sort_order": 7
        },
        {
            "code": "SSE",
            "name": "South South East",
            "degree_start": 146.25,
            "degree_end": 168.75,
            "system_type": "16",
            "sort_order": 8
        },
        {
            "code": "S",
            "name": "South",
            "degree_start": 168.75,
            "degree_end": 191.25,
            "system_type": "16",
            "sort_order": 9
        },
        {
            "code": "SSW",
            "name": "South South West",
            "degree_start": 191.25,
            "degree_end": 213.75,
            "system_type": "16",
            "sort_order": 10
        },
        {
            "code": "SW",
            "name": "South West",
            "degree_start": 213.75,
            "degree_end": 236.25,
            "system_type": "16",
            "sort_order": 11
        },
        {
            "code": "WSW",
            "name": "West South West",
            "degree_start": 236.25,
            "degree_end": 258.75,
            "system_type": "16",
            "sort_order": 12
        },
        {
            "code": "W",
            "name": "West",
            "degree_start": 258.75,
            "degree_end": 281.25,
            "system_type": "16",
            "sort_order": 13
        },
        {
            "code": "WNW",
            "name": "West North West",
            "degree_start": 281.25,
            "degree_end": 303.75,
            "system_type": "16",
            "sort_order": 14
        },
        {
            "code": "NW",
            "name": "North West",
            "degree_start": 303.75,
            "degree_end": 326.25,
            "system_type": "16",
            "sort_order": 15
        },
        {
            "code": "NNW",
            "name": "North North West",
            "degree_start": 326.25,
            "degree_end": 348.75,
            "system_type": "16",
            "sort_order": 16
        }
    ]

    for item in directions:

        exists = db.query(Direction).filter(
            Direction.code == item["code"],
            Direction.system_type == item["system_type"]
        ).first()

        if not exists:
            db.add(Direction(**item))

    db.commit()

    # =====================================================
    # REPORT ENTITIES
    # =====================================================

    entities = [

        # ROOMS

        {
            "slug": "kitchen",
            "name": "Kitchen",
            "category": "room"
        },
        {
            "slug": "bedroom",
            "name": "Bedroom",
            "category": "room"
        },
        {
            "slug": "master-bedroom",
            "name": "Master Bedroom",
            "category": "room"
        },
        {
            "slug": "toilet",
            "name": "Toilet",
            "category": "room"
        },
        {
            "slug": "pooja-room",
            "name": "Pooja Room",
            "category": "room"
        },
        {
            "slug": "living-room",
            "name": "Living Room",
            "category": "room"
        },
        {
            "slug": "dining-room",
            "name": "Dining Room",
            "category": "room"
        },

        # OBJECTS

        {
            "slug": "staircase",
            "name": "Staircase",
            "category": "object"
        },
        {
            "slug": "borewell",
            "name": "Borewell",
            "category": "object"
        },
        {
            "slug": "septic-tank",
            "name": "Septic Tank",
            "category": "object"
        },
        {
            "slug": "underground-water-tank",
            "name": "Underground Water Tank",
            "category": "object"
        },
        {
            "slug": "overhead-water-tank",
            "name": "Overhead Water Tank",
            "category": "object"
        },
    ]

    for item in entities:

        exists = db.query(ReportEntity).filter(
            ReportEntity.slug == item["slug"]
        ).first()

        if not exists:
            db.add(ReportEntity(**item))

    db.commit()

    print("✅ Seeding completed successfully.")

    db.close()


if __name__ == "__main__":
    seed()