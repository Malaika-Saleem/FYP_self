from pymongo import MongoClient
from uuid import uuid4
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/detectifai"))
db = client.get_default_database()
users = db.users
video_files = db.video_files
event_descriptions = db.event_descriptions
subscription_plans = db.subscription_plans
events = db.events

# Add sample user if not exists
sample_user = {
    "user_id": str(uuid4()),
    "username": "testuser",
    "email": "user@detectifai.test",
    "password": "userpass",
    "role": "user",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "last_login": None
}
if users.count_documents({"email": "user@detectifai.test"}) == 0:
    users.insert_one(sample_user)
    print("Added sample user: user@detectifai.test / userpass")
else:
    print("Sample user already exists")

# Add sample subscription plans
sample_plans = [
    {
        "plan_id": str(uuid4()),
        "plan_name": "Basic",
        "description": "Basic surveillance features",
        "price": 9.99,
        "features": "basic_ai,email_support",
        "storage_limit": 10,
        "is_active": True
    },
    {
        "plan_id": str(uuid4()),
        "plan_name": "Pro",
        "description": "Advanced AI features with priority support",
        "price": 29.99,
        "features": "advanced_ai,priority_support,face_recognition",
        "storage_limit": 100,
        "is_active": True
    },
    {
        "plan_id": str(uuid4()),
        "plan_name": "Enterprise",
        "description": "Full enterprise features with 24/7 support",
        "price": 99.99,
        "features": "premium_ai,24_7_support,face_recognition,custom_integrations",
        "storage_limit": 1000,
        "is_active": True
    }
]

for plan in sample_plans:
    if subscription_plans.count_documents({"plan_id": plan["plan_id"]}) == 0:
        subscription_plans.insert_one(plan)
        print(f"Added subscription plan: {plan['plan_name']}")
    else:
        print(f"Subscription plan {plan['plan_name']} already exists")

# Get existing video files to add sample events and descriptions
existing_videos = list(video_files.find({}))

if not existing_videos:
    print("No video files found. Upload some videos first, then run this script.")
else:
    # Add sample events and descriptions to the first video
    video = existing_videos[0]
    video_id = video["video_id"]
    
    # Create sample events
    sample_events = [
        {
            "event_id": str(uuid4()),
            "video_id": video_id,
            "event_type": "person_detection",
            "confidence_score": 0.95,
            "start_timestamp_ms": 0,
            "end_timestamp_ms": 5000,
            "bounding_boxes": {"x": 100, "y": 150, "width": 200, "height": 300},
            "visual_embedding": [],
            "is_verified": False,
            "is_false_positive": False,
            "verified_by": None,
            "verified_at": None
        },
        {
            "event_id": str(uuid4()),
            "video_id": video_id,
            "event_type": "object_detection",
            "confidence_score": 0.87,
            "start_timestamp_ms": 5200,
            "end_timestamp_ms": 12800,
            "bounding_boxes": {"x": 300, "y": 200, "width": 150, "height": 100},
            "visual_embedding": [],
            "is_verified": False,
            "is_false_positive": False,
            "verified_by": None,
            "verified_at": None
        }
    ]
    
    # Insert events
    for event in sample_events:
        if events.count_documents({"event_id": event["event_id"]}) == 0:
            events.insert_one(event)
            print(f"Added event: {event['event_type']}")
    
    # Add sample descriptions for the events
    sample_descriptions = [
        {
            "description_id": str(uuid4()),
            "event_id": sample_events[0]["event_id"],
            "caption": "Person walking into the room carrying a briefcase",
            "text_embedding": [],
            "confidence": 0.92,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "description_id": str(uuid4()),
            "event_id": sample_events[1]["event_id"],
            "caption": "Individual sits down at desk and opens laptop computer",
            "text_embedding": [],
            "confidence": 0.88,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    
    # Insert descriptions
    for desc in sample_descriptions:
        if event_descriptions.count_documents({"description_id": desc["description_id"]}) == 0:
            event_descriptions.insert_one(desc)
            print(f"Added description: {desc['caption'][:50]}...")
    
    # If there are more videos, add different events to the second one
    if len(existing_videos) > 1:
        video2 = existing_videos[1]
        video2_id = video2["video_id"]
        
        sample_events2 = [
            {
                "event_id": str(uuid4()),
                "video_id": video2_id,
                "event_type": "security_patrol",
                "confidence_score": 0.93,
                "start_timestamp_ms": 2100,
                "end_timestamp_ms": 15400,
                "bounding_boxes": {"x": 50, "y": 100, "width": 180, "height": 250},
                "visual_embedding": [],
                "is_verified": False,
                "is_false_positive": False,
                "verified_by": None,
                "verified_at": None
            }
        ]
        
        for event in sample_events2:
            if events.count_documents({"event_id": event["event_id"]}) == 0:
                events.insert_one(event)
                print(f"Added event: {event['event_type']}")
        
        sample_descriptions2 = [
            {
                "description_id": str(uuid4()),
                "event_id": sample_events2[0]["event_id"],
                "caption": "Security guard patrolling the hallway with flashlight",
                "text_embedding": [],
                "confidence": 0.91,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]
        
        for desc in sample_descriptions2:
            if event_descriptions.count_documents({"description_id": desc["description_id"]}) == 0:
                event_descriptions.insert_one(desc)
                print(f"Added description: {desc['caption'][:50]}...")

print("\n--- Database Seeding Complete ---")
print("You can now test search functionality with terms like:")
print("- 'briefcase' or 'laptop'")
print("- 'security' or 'guard'") 
print("- 'person' or 'detection'")
print("- 'desk' or 'computer'")
print("- 'patrol' or 'hallway'")

# Show summary
total_videos = video_files.count_documents({})
total_events = events.count_documents({})
total_descriptions = event_descriptions.count_documents({})
total_users = users.count_documents({})
total_plans = subscription_plans.count_documents({})

print(f"\nDatabase Summary:")
print(f"Total users: {total_users}")
print(f"Total subscription plans: {total_plans}")
print(f"Total video files: {total_videos}")
print(f"Total events: {total_events}")
print(f"Total event descriptions: {total_descriptions}")
