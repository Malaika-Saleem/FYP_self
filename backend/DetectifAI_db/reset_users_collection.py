from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def reset_users_collection():
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_default_database()
        
        # Drop the existing users collection
        print("Dropping existing users collection...")
        db.users.drop()
        
        # Run database_setup.py to recreate with new schema
        print("Creating users collection with new schema...")
        import database_setup
        
        print("✅ Users collection reset successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    reset_users_collection()