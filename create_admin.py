#!/usr/bin/env python
import sys
import os

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password

def create_admin():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        
        if not admin:
            admin_user = User(
                name="Administrator",
                email="admin@example.com",
                phone="9999999998",
                password=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("=" * 50)
            print("✅ Admin user created successfully!")
            print("=" * 50)
            print(f"Email: admin@example.com")
            print(f"Password: admin123")
            print("=" * 50)
            print("⚠️  Please change this password after first login!")
        else:
            print("ℹ️  Admin user already exists")
            print(f"Email: {admin.email}")
            print(f"Role: {admin.role}")
            
    except Exception as e:
        print(f"❌ Error creating admin: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()