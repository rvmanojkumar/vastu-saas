from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models import *
from app.core.security import hash_password
from datetime import datetime, timedelta

# List of tables in correct order for deletion (dependent tables first)
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
    "user_subscriptions",
    "subscriptions",
    "user_roles",
    "role_permissions",
    "permissions",
    "roles",
    "users",
    "plans",
    "directions",
    "languages",
    "tasks",
    "reports",
    "rules",
]

def truncate_all_tables(db: Session):
    """Truncate all tables to reset data for MySQL"""
    print("⚠️  Truncating all tables...")
    
    # Disable foreign key checks for MySQL
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    
    for table in TABLES_ORDER:
        try:
            # Try TRUNCATE first
            db.execute(text(f"TRUNCATE TABLE `{table}`;"))
            print(f"  ✓ Truncated {table}")
        except Exception as e:
            try:
                # If TRUNCATE fails (due to foreign keys), try DELETE
                db.execute(text(f"DELETE FROM `{table}`;"))
                # Reset auto-increment
                db.execute(text(f"ALTER TABLE `{table}` AUTO_INCREMENT = 1;"))
                print(f"  ✓ Cleared and reset {table}")
            except Exception as e2:
                print(f"  ✗ Failed to clear {table}: {str(e2)}")
    
    # Re-enable foreign key checks
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    db.commit()
    print("✅ All tables truncated successfully!\n")

def seed():
    db: Session = SessionLocal()
    
    try:
        # =====================================================
        # LANGUAGES
        # =====================================================
        print("Seeding languages...")
        languages = [
            {"code": "en", "name": "English", "is_default": True},
        ]
        
        for item in languages:
            exists = db.query(Language).filter(Language.code == item["code"]).first()
            if not exists:
                db.add(Language(**item))
        db.commit()
        print("  ✓ Languages seeded")

        # =====================================================
        # DIRECTIONS (16 SYSTEM)
        # =====================================================
        print("Seeding directions...")
        directions = [
            {"code": "N", "name": "North", "degree_start": 348.75, "degree_end": 11.25, "system_type": "16", "sort_order": 1},
            {"code": "NNE", "name": "North North East", "degree_start": 11.25, "degree_end": 33.75, "system_type": "16", "sort_order": 2},
            {"code": "NE", "name": "North East", "degree_start": 33.75, "degree_end": 56.25, "system_type": "16", "sort_order": 3},
            {"code": "ENE", "name": "East North East", "degree_start": 56.25, "degree_end": 78.75, "system_type": "16", "sort_order": 4},
            {"code": "E", "name": "East", "degree_start": 78.75, "degree_end": 101.25, "system_type": "16", "sort_order": 5},
            {"code": "ESE", "name": "East South East", "degree_start": 101.25, "degree_end": 123.75, "system_type": "16", "sort_order": 6},
            {"code": "SE", "name": "South East", "degree_start": 123.75, "degree_end": 146.25, "system_type": "16", "sort_order": 7},
            {"code": "SSE", "name": "South South East", "degree_start": 146.25, "degree_end": 168.75, "system_type": "16", "sort_order": 8},
            {"code": "S", "name": "South", "degree_start": 168.75, "degree_end": 191.25, "system_type": "16", "sort_order": 9},
            {"code": "SSW", "name": "South South West", "degree_start": 191.25, "degree_end": 213.75, "system_type": "16", "sort_order": 10},
            {"code": "SW", "name": "South West", "degree_start": 213.75, "degree_end": 236.25, "system_type": "16", "sort_order": 11},
            {"code": "WSW", "name": "West South West", "degree_start": 236.25, "degree_end": 258.75, "system_type": "16", "sort_order": 12},
            {"code": "W", "name": "West", "degree_start": 258.75, "degree_end": 281.25, "system_type": "16", "sort_order": 13},
            {"code": "WNW", "name": "West North West", "degree_start": 281.25, "degree_end": 303.75, "system_type": "16", "sort_order": 14},
            {"code": "NW", "name": "North West", "degree_start": 303.75, "degree_end": 326.25, "system_type": "16", "sort_order": 15},
            {"code": "NNW", "name": "North North West", "degree_start": 326.25, "degree_end": 348.75, "system_type": "16", "sort_order": 16},
        ]
        
        for item in directions:
            exists = db.query(Direction).filter(
                Direction.code == item["code"],
                Direction.system_type == item["system_type"]
            ).first()
            if not exists:
                db.add(Direction(**item))
        db.commit()
        print("  ✓ Directions seeded")

        # =====================================================
        # REPORT ENTITIES (Rooms and Objects)
        # =====================================================
        print("Seeding report entities...")
        entities = [
            # ROOMS
            {"slug": "kitchen", "name": "Kitchen", "category": "room", "sort_order": 1},
            {"slug": "bedroom", "name": "Bedroom", "category": "room", "sort_order": 2},
            {"slug": "master-bedroom", "name": "Master Bedroom", "category": "room", "sort_order": 3},
            {"slug": "toilet", "name": "Toilet", "category": "room", "sort_order": 4},
            {"slug": "pooja-room", "name": "Pooja Room", "category": "room", "sort_order": 5},
            {"slug": "living-room", "name": "Living Room", "category": "room", "sort_order": 6},
            {"slug": "dining-room", "name": "Dining Room", "category": "room", "sort_order": 7},
            # OBJECTS
            {"slug": "staircase", "name": "Staircase", "category": "object", "sort_order": 8},
            {"slug": "borewell", "name": "Borewell", "category": "object", "sort_order": 9},
            {"slug": "septic-tank", "name": "Septic Tank", "category": "object", "sort_order": 10},
            {"slug": "underground-water-tank", "name": "Underground Water Tank", "category": "object", "sort_order": 11},
            {"slug": "overhead-water-tank", "name": "Overhead Water Tank", "category": "object", "sort_order": 12},
        ]
        
        for item in entities:
            exists = db.query(ReportEntity).filter(ReportEntity.slug == item["slug"]).first()
            if not exists:
                db.add(ReportEntity(**item))
        db.commit()
        print("  ✓ Report entities seeded")

        # =====================================================
        # USERS (with proper password hashing)
        # =====================================================
        print("Seeding users...")
        
        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin_user = User(
                name="Administrator",
                email="admin@example.com",
                phone="9999999999",
                password=hash_password("admin123"),
                role="admin",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(admin_user)
        
        # Demo user
        demo_user = db.query(User).filter(User.email == "demo@test.com").first()
        if not demo_user:
            demo_user = User(
                name="Demo User",
                email="demo@test.com",
                phone="8888888888",
                password=hash_password("demo123"),
                role="user",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(demo_user)
        
        db.commit()
        print("  ✓ Users seeded")

        # =====================================================
        # PLANS
        # =====================================================
        print("Seeding plans...")
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
        print("  ✓ Plans seeded")

        # =====================================================
        # SUBSCRIPTIONS
        # =====================================================
        print("Seeding subscriptions...")
        user = db.query(User).filter(User.email == "demo@test.com").first()
        if user:
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
        print("  ✓ Subscriptions seeded")

        # =====================================================
        # PROJECT
        # =====================================================
        print("Seeding projects...")
        user = db.query(User).filter(User.email == "demo@test.com").first()
        if user:
            existing_project = db.query(Project).filter(Project.id == 1).first()
            if not existing_project:
                project = Project(
                    id=1,
                    user_id=user.id,
                    name="Demo Project",
                    description="Test project for Vastu analysis",
                    image_path=None,
                    rotation=0,
                    starting_degree=0
                )
                db.add(project)
                db.commit()
        print("  ✓ Projects seeded")

        print("\n" + "="*50)
        print("✅ Seeding completed successfully!")
        print("="*50)
        print("\n📋 Login Credentials:")
        print("  Admin: admin@example.com / admin123")
        print("  Demo:  demo@test.com / demo123")
        print("="*50)

    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def reset_and_seed():
    """Truncate all tables and run seed"""
    db = SessionLocal()
    try:
        truncate_all_tables(db)
        db.close()
        seed()
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_and_seed()
    else:
        seed()