from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from models.user import get_all_reminder_users, can_use_bot, users_col
from services.whatsapp import send_text
import pytz
import logging

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def check_watering_reminders():
    logger.info("[Scheduler] Checking watering reminders...")
    users = get_all_reminder_users()
    today = datetime.utcnow()

    for user in users:
        if not can_use_bot(user):
            continue

        plants_to_water = []
        for plant in user.get("plants", []):
            last_watered = plant.get("last_watered", today)
            days_since = (today - last_watered).days
            if days_since >= plant.get("watering_frequency_days", 2):
                plants_to_water.append(plant)

        if not plants_to_water:
            continue

        plant_lines = "\n".join(f"🌿 {p['name']}" for p in plants_to_water)
        message = (
            f"💧 Good morning! Time to water your plants:\n\n{plant_lines}\n\n"
            f"Reply 'watered' to reset the timer, or send a photo for a health check!"
        )

        try:
            send_text(user["phone"], message)

            # Reset last_watered for due plants
            updated_plants = []
            due_names = {p["name"] for p in plants_to_water}
            for plant in user.get("plants", []):
                if plant["name"] in due_names:
                    plant["last_watered"] = today
                updated_plants.append(plant)

            users_col.update_one(
                {"phone": user["phone"]},
                {"$set": {"plants": updated_plants}}
            )
            logger.info(f"[Scheduler] Reminded {user['phone']} about {len(plants_to_water)} plant(s)")
        except Exception as e:
            logger.error(f"[Scheduler] Failed to remind {user['phone']}: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(
        check_watering_reminders,
        CronTrigger(hour=7, minute=30, timezone=IST),
        id="watering_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] Watering reminder scheduler started (7:30 AM IST daily)")
    return scheduler
