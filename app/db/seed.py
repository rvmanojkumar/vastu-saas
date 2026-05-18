from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.core.security import hash_password

# Explicit imports (IMPORTANT for production safety)
from app.models.user import User
from app.models.plan import Plan
from app.models.language import Language
from app.models.direction import Direction
from app.models.report_entity import ReportEntity
from app.models.subscription import Subscription
from app.models.project import Project


# =====================================================
# TABLE ORDER (for reset only)
# =====================================================
TABLES_ORDER = [
    "report_items",
    "generated_reports",
    "report_rules",
    "report_entities",
    "translations",
    "project_objects",
    "objects",
    "polygons",
    "projects",
    "subscriptions",
    "users",
    "plans",
    "directions",
    "languages",
]


# =====================================================
# RESET TABLES
# =====================================================
def truncate_all_tables(db: Session):
    print("⚠️ Truncating all tables...")

    db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

    for table in TABLES_ORDER:
        try:
            db.execute(text(f"TRUNCATE TABLE `{table}`;"))
            print(f"  ✓ {table}")
        except Exception:
            try:
                db.execute(text(f"DELETE FROM `{table}`;"))
                db.execute(text(f"ALTER TABLE `{table}` AUTO_INCREMENT = 1;"))
                print(f"  ✓ Cleared {table}")
            except Exception as e:
                print(f"  ✗ Failed {table}: {e}")

    db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    db.commit()
    print("✅ Reset completed\n")


# =====================================================
# SEED DATA
# =====================================================
def seed():
    db: Session = SessionLocal()

    try:
        print("🚀 Starting seed...")

        # ---------------------
        # LANGUAGES
        # ---------------------
        languages = [
            {"code": "en", "name": "English", "is_default": True},
        ]

        for item in languages:
            if not db.query(Language).filter_by(code=item["code"]).first():
                db.add(Language(**item))

        # ---------------------
        # DIRECTIONS
        # ---------------------
        directions = [
            {"code": "N", "name": "North", "degree_start": 348.75, "degree_end": 11.25, "system_type": "16", "sort_order": 1},
            {"code": "NE", "name": "North East", "degree_start": 33.75, "degree_end": 56.25, "system_type": "16", "sort_order": 3},
            {"code": "E", "name": "East", "degree_start": 78.75, "degree_end": 101.25, "system_type": "16", "sort_order": 5},
            {"code": "S", "name": "South", "degree_start": 168.75, "degree_end": 191.25, "system_type": "16", "sort_order": 9},
            {"code": "W", "name": "West", "degree_start": 258.75, "degree_end": 281.25, "system_type": "16", "sort_order": 13},
        ]

        for item in directions:
            if not db.query(Direction).filter_by(
                code=item["code"],
                system_type=item["system_type"]
            ).first():
                db.add(Direction(**item))

        # ---------------------
        # REPORT ENTITIES
        # ---------------------
        entities = [
            {"slug": "kitchen", "name": "Kitchen", "category": "room"},
            {"slug": "bedroom", "name": "Bedroom", "category": "room"},
            {"slug": "pooja-room", "name": "Pooja Room", "category": "room"},
            {"slug": "staircase", "name": "Staircase", "category": "object"},
            {"slug": "borewell", "name": "Borewell", "category": "object"},
        ]

        for item in entities:
            if not db.query(ReportEntity).filter_by(slug=item["slug"]).first():
                db.add(ReportEntity(**item))

        # ---------------------
        # USERS
        # ---------------------
        if not db.query(User).filter_by(email="admin@example.com").first():
            db.add(User(
                name="Administrator",
                email="admin@example.com",
                phone="9999999999",
                password=hash_password("admin123"),
                role="admin",
                is_active=True,
                created_at=datetime.utcnow()
            ))

        if not db.query(User).filter_by(email="demo@test.com").first():
            db.add(User(
                name="Demo User",
                email="demo@test.com",
                phone="8888888888",
                password=hash_password("demo123"),
                role="user",
                is_active=True,
                created_at=datetime.utcnow()
            ))

        # ---------------------
        # PLANS
        # ---------------------
        if not db.query(Plan).filter_by(name="Pro Plan").first():
            db.add(Plan(
                name="Pro Plan",
                price=999,
                duration_days=30,
                report_limit=20,
                is_whitelabel=True
            ))

        # ---------------------
        # SUBSCRIPTION
        # ---------------------
        user = db.query(User).filter_by(email="demo@test.com").first()
        if user and not db.query(Subscription).filter_by(user_id=user.id).first():
            db.add(Subscription(
                user_id=user.id,
                plan_name="Pro Plan",
                status="active",
                reports_limit=20,
                reports_used=0,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30)
            ))

        # ---------------------
        # PROJECT
        # ---------------------
        if user and not db.query(Project).filter_by(name="Demo Project").first():
            db.add(Project(
                user_id=user.id,
                name="Demo Project",
                description="Test project for Vastu analysis",
                rotation=0,
                starting_degree=0
            ))

        # SINGLE COMMIT (IMPORTANT)
        db.commit()

        print("🎉 Seeding completed successfully!")
        print("\nLogin:")
        print("Admin: admin@example.com / admin123")
        print("Demo:  demo@test.com / demo123")

    except Exception as e:
        db.rollback()
        print("❌ Seeding failed:", e)
        raise

    finally:
        db.close()


# =====================================================
# RESET + SEED
# =====================================================
def reset_and_seed():
    db = SessionLocal()
    try:
        truncate_all_tables(db)
    finally:
        db.close()

    seed()


# =====================================================
# CLI ENTRY
# =====================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_and_seed()
    else:
        seed()