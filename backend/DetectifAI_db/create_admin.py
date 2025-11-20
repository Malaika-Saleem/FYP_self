#!/usr/bin/env python3
"""
Script to create an admin user in the DetectifAI database
"""

from pymongo import MongoClient
from uuid import uuid4
from datetime import datetime, timezone
import bcrypt
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def create_admin_user():
    """Create an admin user in the database"""
    
    # Get MongoDB connection
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/detectifai")
    client = MongoClient(mongo_uri)
    db = client.get_default_database()
    users = db.users
    
    # Admin credentials (change these!)
    admin_email = "admin@detectifai.com"
    admin_password = "admin123"  # ⚠️ CHANGE THIS PASSWORD!
    admin_username = "admin"
    
    # Check if admin already exists
    existing_admin = users.find_one({"email": admin_email})
    if existing_admin:
        print(f"⚠️  Admin user with email '{admin_email}' already exists!")
        update = input("Do you want to update the password? (y/n): ").lower().strip()
        if update == 'y':
            new_password = input("Enter new password: ").strip()
            if not new_password:
                print("❌ Password cannot be empty")
                sys.exit(1)
            
            # Hash new password
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update admin user
            users.update_one(
                {"email": admin_email},
                {
                    "$set": {
                        "password_hash": password_hash,
                        "password": new_password,  # For Flask backend compatibility
                        "role": "admin",
                        "is_active": True,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            print(f"✅ Admin password updated successfully!")
            print(f"   Email: {admin_email}")
            print(f"   Password: {new_password}")
        else:
            print("ℹ️  Keeping existing admin user")
        client.close()
        return
    
    # Create new admin user
    print(f"Creating admin user...")
    print(f"   Email: {admin_email}")
    print(f"   Username: {admin_username}")
    
    # Hash password
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin_user = {
        "user_id": str(uuid4()),
        "username": admin_username,
        "email": admin_email,
        "password_hash": password_hash,
        "password": admin_password,  # For Flask backend compatibility (plain text - TODO: remove in production)
        "role": "admin",
        "is_active": True,
        "profile_data": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None
    }
    
    try:
        users.insert_one(admin_user)
        print("\n✅ Admin user created successfully!")
        print(f"\n📋 Login Credentials:")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"\n⚠️  IMPORTANT: Change this password after first login!")
        print(f"\n🌐 Access the admin panel at: http://localhost:3000/admin/signin")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DetectifAI - Admin User Creation Script")
    print("=" * 60)
    print()
    
    # Check if MONGO_URI is set
    if not os.getenv("MONGO_URI"):
        print("❌ Error: MONGO_URI environment variable not set")
        print("Please create a .env file with your MongoDB connection string")
        print("Example: MONGO_URI=mongodb://localhost:27017/detectifai")
        sys.exit(1)
    
    create_admin_user()
    print("\n" + "=" * 60)
    print("✅ Script completed!")
    print("=" * 60)



