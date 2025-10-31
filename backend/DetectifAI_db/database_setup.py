from pymongo import MongoClient, ASCENDING
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client.get_default_database()


def create_collection_if_not_exists(name, validator=None, indexes=None):
    """Create collection if it doesn't exist, otherwise skip"""
    try:
        if validator:
            db.create_collection(name, validator=validator)
        else:
            db.create_collection(name)
        print(f"Created collection: {name}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Collection {name} already exists, skipping...")
        else:
            print(f"Error creating collection {name}: {e}")
            return False

    # Create indexes if specified
    if indexes:
        for index in indexes:
            try:
                if isinstance(index, tuple):
                    # Index with options
                    db[name].create_index(index[0], **index[1])
                else:
                    # Simple index
                    db[name].create_index(index)
                print(f"  Created index on {name}")
            except Exception as e:
                if "already exists" in str(e) or "duplicate key" in str(e):
                    print(f"  Index on {name} already exists")
                else:
                    print(f"  Error creating index on {name}: {e}")
    return True


# === ADMIN ===
create_collection_if_not_exists("admin", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["admin_id", "username", "email", "password"],
        "properties": {
            "admin_id": {"bsonType": "string"},
            "username": {"bsonType": "string"},
            "email": {"bsonType": "string"},
            "password": {"bsonType": "string"},
            "role": {"bsonType": "string"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "last_login": {"bsonType": ["date", "null"]}
        }
    }
}, indexes=[([("email", ASCENDING)], {"unique": True}), "username"])


# === USERS ===
create_collection_if_not_exists("users", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id", "email"],
        "properties": {
            "user_id": {"bsonType": "string"},
            "username": {"bsonType": "string"},
            "email": {"bsonType": "string"},
            "password_hash": {"bsonType": "string"},
            "role": {"bsonType": "string"},
            "profile_data": {"bsonType": "object"},
            "is_active": {"bsonType": "bool"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "last_login": {"bsonType": ["date", "null"]}
        }
    }
}, indexes=[([("email", ASCENDING)], {"unique": True}), "username"])


# === VIDEO FILES ===
create_collection_if_not_exists("video_files", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["video_id", "user_id", "file_path"],
        "properties": {
            "video_id": {"bsonType": "string"},
            "user_id": {"bsonType": "string"},
            "file_path": {"bsonType": "string"},
            "minio_object_key": {"bsonType": "string"},
            "minio_bucket": {"bsonType": "string"},
            "codec": {"bsonType": "string"},
            "fps": {"bsonType": "double"},
            "upload_date": {"bsonType": "date"},
            "duration_secs": {"bsonType": "int"},
            "file_size_bytes": {"bsonType": "long"},
            "meta_data": {"bsonType": "object"}
        }
    }
}, indexes=["user_id", "upload_date"])


# === EVENTS ===
create_collection_if_not_exists("events", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["event_id", "video_id", "start_timestamp_ms", "end_timestamp_ms"],
        "properties": {
            "event_id": {"bsonType": "string"},
            "video_id": {"bsonType": "string"},
            "start_timestamp_ms": {"bsonType": "long"},
            "end_timestamp_ms": {"bsonType": "long"},
            "confidence_score": {"bsonType": "double"},
            "is_verified": {"bsonType": "bool"},
            "is_false_positive": {"bsonType": "bool"},
            "verified_at": {"bsonType": ["date", "null"]},
            "verified_by": {"bsonType": ["string", "null"]},
            "visual_embedding": {"bsonType": "array"},
            "bounding_boxes": {"bsonType": "object"},
            "event_type": {"bsonType": "string"}
        }
    }
}, indexes=["video_id", "event_type", "is_verified"])


# === EVENT CLIPS ===
create_collection_if_not_exists("event_clips", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["clip_id", "event_id", "clip_path"],
        "properties": {
            "clip_id": {"bsonType": "string"},
            "event_id": {"bsonType": "string"},
            "clip_path": {"bsonType": "string"},
            "thumbnail_path": {"bsonType": "string"},
            "minio_object_key": {"bsonType": "string"},
            "minio_bucket": {"bsonType": "string"},
            "duration_ms": {"bsonType": "long"},
            "extracted_at": {"bsonType": "date"},
            "file_size_bytes": {"bsonType": "long"}
        }
    }
}, indexes=["event_id"])


# === DETECTED FACES ===
create_collection_if_not_exists("detected_faces", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["face_id", "event_id", "detected_at"],
        "properties": {
            "face_id": {"bsonType": "string"},
            "event_id": {"bsonType": "string"},
            "detected_at": {"bsonType": "date"},
            "confidence_score": {"bsonType": "double"},
            "face_embedding": {"bsonType": "array"},
            "minio_object_key": {"bsonType": "string"},
            "minio_bucket": {"bsonType": "string"},
            "face_image_path": {"bsonType": "string"},
            "bounding_boxes": {"bsonType": "object"}
        }
    }
}, indexes=["event_id", "detected_at"])


# === FACE MATCHES ===
create_collection_if_not_exists("face_matches", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["match_id", "face_id_1", "face_id_2", "similarity_score"],
        "properties": {
            "match_id": {"bsonType": "string"},
            "face_id_1": {"bsonType": "string"},
            "face_id_2": {"bsonType": "string"},
            "similarity_score": {"bsonType": "double"},
            "matched_at": {"bsonType": "date"}
        }
    }
}, indexes=["face_id_1", "face_id_2", "similarity_score"])


# === EVENT DESCRIPTIONS ===
create_collection_if_not_exists("event_descriptions", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["description_id", "event_id", "text_embedding"],
        "properties": {
            "description_id": {"bsonType": "string"},
            "event_id": {"bsonType": "string"},
            "text_embedding": {"bsonType": "array"},
            "caption": {"bsonType": "string"},
            "confidence": {"bsonType": "double"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"}
        }
    }
}, indexes=["event_id", "created_at"])


# === EVENT CAPTIONS ===
create_collection_if_not_exists("event_captions", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["description_id", "description"],
        "properties": {
            "description_id": {"bsonType": "string"},
            "description": {"bsonType": "string"}
        }
    }
}, indexes=["description_id"])


# === QUERY ===
create_collection_if_not_exists("query", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["query_id", "user_id", "query_text"],
        "properties": {
            "query_id": {"bsonType": "string"},
            "user_id": {"bsonType": "string"},
            "query_text": {"bsonType": "string"},
            "query_embedding": {"bsonType": "array"},
            "executed_at": {"bsonType": "date"}
        }
    }
}, indexes=["user_id", "executed_at"])


# === QUERY RESULT ===
create_collection_if_not_exists("query_result", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["result_id", "query_id", "event_id"],
        "properties": {
            "result_id": {"bsonType": "string"},
            "query_id": {"bsonType": "string"},
            "event_id": {"bsonType": "string"},
            "relevance_score": {"bsonType": "double"},
            "match_details": {"bsonType": "object"},
            "returned_at": {"bsonType": "date"}
        }
    }
}, indexes=["query_id", "event_id", "relevance_score"])


# === SUBSCRIPTION PLANS ===
create_collection_if_not_exists("subscription_plans", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["plan_id", "plan_name", "price"],
        "properties": {
            "plan_id": {"bsonType": "string"},
            "plan_name": {"bsonType": "string"},
            "description": {"bsonType": "string"},
            "price": {"bsonType": "decimal"},
            "features": {"bsonType": "string"},
            "storage_limit": {"bsonType": "int"},
            "is_active": {"bsonType": "bool"}
        }
    }
}, indexes=[([("plan_id", ASCENDING)], {"unique": True}), "is_active"])


# === USER SUBSCRIPTIONS ===
create_collection_if_not_exists("user_subscriptions", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["subscription_id", "user_id", "plan_id"],
        "properties": {
            "subscription_id": {"bsonType": "string"},
            "user_id": {"bsonType": "string"},
            "plan_id": {"bsonType": "string"},
            "start_date": {"bsonType": "date"},
            "end_date": {"bsonType": "date"}
        }
    }
}, indexes=["user_id", "plan_id", "start_date"])


# === USER SESSIONS ===
create_collection_if_not_exists("user_sessions", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["session_id", "user_id", "session_token", "expires_at"],
        "properties": {
            "session_id": {"bsonType": "string"},
            "user_id": {"bsonType": "string"},
            "session_token": {"bsonType": "string"},
            "expires_at": {"bsonType": "date"},
            "ip_address": {"bsonType": "string"},
            "user_agent": {"bsonType": "string"},
            "created_at": {"bsonType": "date"}
        }
    }
}, indexes=[
    ([("session_token", ASCENDING)], {"unique": True}),
    "user_id",
    "expires_at"
])


print("\nDatabase schema setup completed successfully.")
print("All collections are ready with validation and indexes.")
