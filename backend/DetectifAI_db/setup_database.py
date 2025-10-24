#!/usr/bin/env python3
"""
Database setup script for DetectifAI backend
This script initializes the MongoDB database with the required collections and indexes.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if MONGO_URI is set
if not os.getenv("MONGO_URI"):
    print("❌ Error: MONGO_URI environment variable not set")
    print("Please create a .env file with your MongoDB connection string")
    print("Example: MONGO_URI=mongodb://localhost:27017/detectifai")
    sys.exit(1)

try:
    # Import and run database setup
    from database_setup import *
    print("\n✅ Database setup completed successfully!")
    
    # Ask if user wants to seed the database
    seed_choice = input("\nWould you like to seed the database with sample data? (y/n): ").lower().strip()
    
    if seed_choice in ['y', 'yes']:
        print("\n🌱 Seeding database with sample data...")
        from database_seed import *
        print("\n✅ Database seeding completed!")
    else:
        print("\n⏭️  Skipping database seeding")
    
    print("\n🎉 Database initialization complete!")
    print("\nNext steps:")
    print("1. Start the integrated Flask app: python app_integrated.py")
    print("2. Or start the original app: python app.py")
    print("3. Test the API endpoints at http://localhost:5000")
    
except Exception as e:
    print(f"❌ Error during database setup: {e}")
    sys.exit(1)
