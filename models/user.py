from pymongo import MongoClient
from datetime import datetime, timedelta
import os

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["plantbot"]
users_col = db["users"]


def get_or_create_user(phone: str) -> dict:
    user = users_col.find_one({"phone": phone})
    if not user:
        user = {
            "phone": phone,
            "name": "Friend",
            "conversation_count": 0,
            "is_premium": False,
            "premium_expires_at": None,
            "latitude": 28.6139,   # Default: Delhi
            "longitude": 77.2090,
            "plants": [],
            "reminders_enabled": True,
            "created_at": datetime.utcnow(),
        }
        users_col.insert_one(user)
    return user


def can_use_bot(user: dict) -> bool:
    if user.get("is_premium"):
        expires = user.get("premium_expires_at")
        if expires and expires < datetime.utcnow():
            users_col.update_one({"phone": user["phone"]}, {"$set": {"is_premium": False}})
            return False
        return True
    limit = int(os.getenv("FREE_CONVERSATION_LIMIT", 20))
    return user.get("conversation_count", 0) < limit


def remaining_free(user: dict) -> int:
    limit = int(os.getenv("FREE_CONVERSATION_LIMIT", 20))
    return max(0, limit - user.get("conversation_count", 0))


def increment_count(phone: str):
    users_col.update_one({"phone": phone}, {"$inc": {"conversation_count": 1}})


def activate_premium(phone: str):
    users_col.update_one(
        {"phone": phone},
        {"$set": {
            "is_premium": True,
            "premium_since": datetime.utcnow(),
            "premium_expires_at": datetime.utcnow() + timedelta(days=30),
        }}
    )


def add_plant(phone: str, name: str, watering_days: int):
    plant = {
        "name": name,
        "watering_frequency_days": watering_days,
        "last_watered": datetime.utcnow(),
        "added_at": datetime.utcnow(),
    }
    users_col.update_one({"phone": phone}, {"$push": {"plants": plant}})


def remove_plant(phone: str, name: str) -> bool:
    result = users_col.update_one(
        {"phone": phone},
        {"$pull": {"plants": {"name": {"$regex": f"^{name}$", "$options": "i"}}}}
    )
    return result.modified_count > 0


def mark_all_watered(phone: str):
    user = users_col.find_one({"phone": phone})
    if not user:
        return
    plants = user.get("plants", [])
    for p in plants:
        p["last_watered"] = datetime.utcnow()
    users_col.update_one({"phone": phone}, {"$set": {"plants": plants}})


def set_reminders(phone: str, enabled: bool):
    users_col.update_one({"phone": phone}, {"$set": {"reminders_enabled": enabled}})


def get_all_reminder_users() -> list:
    return list(users_col.find({"reminders_enabled": True}))
