import os
import re
import json
import requests
from flask import Blueprint, request, jsonify
from datetime import datetime

from models.user import (
    get_or_create_user, add_plant, remove_plant,
    mark_all_watered, set_reminders, activate_premium, users_col
)
from services.gemini import analyze_plant_photo, get_weather_advice, answer_plant_question
from services.whatsapp import send_text, send_welcome
from middleware.freemium import check_freemium

webhook_bp = Blueprint("webhook", __name__)


# ── Meta webhook verification ──────────────────────────────────────────────
@webhook_bp.get("/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == os.getenv("META_VERIFY_TOKEN"):
        return challenge, 200
    return "Forbidden", 403


# ── Incoming messages ──────────────────────────────────────────────────────
@webhook_bp.post("/webhook")
def handle_message():
    # Always respond 200 immediately to Meta
    data = request.get_json(silent=True) or {}

    try:
        entry = data.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        message = change.get("value", {}).get("messages", [{}])[0]
        if not message:
            return jsonify(ok=True)

        phone = message["from"]
        msg_type = message.get("type")  # 'text' or 'image'
        user = get_or_create_user(phone)

        # ── Non-AI commands (always free) ──────────────────────────────────
        if msg_type == "text":
            text = message["text"]["body"].strip()
            text_lower = text.lower()

            if text_lower == "paid":
                send_text(phone,
                    "✅ We received your payment request!\n\n"
                    "Our team will verify and activate your Premium within a few minutes.\n\n"
                    "Thank you for supporting PlantCare Bot! 🌿"
                )
                return jsonify(ok=True)

            if text_lower == "stop reminders":
                set_reminders(phone, False)
                send_text(phone, "🔕 Reminders turned off. Send 'start reminders' anytime to turn them back on.")
                return jsonify(ok=True)

            if text_lower == "start reminders":
                set_reminders(phone, True)
                send_text(phone, "🔔 Reminders turned on! You'll hear from me every morning if your plants need water.")
                return jsonify(ok=True)

            if text_lower == "watered":
                mark_all_watered(phone)
                send_text(phone, "💧 Great job! I've reset the watering timer for all your plants. They thank you! 🌱")
                return jsonify(ok=True)

            if text_lower == "my plants":
                plants = user.get("plants", [])
                if not plants:
                    send_text(phone, "🪴 You haven't added any plants yet!\n\nAdd one like this:\n'add plant Rose, 3 days'")
                else:
                    today = datetime.utcnow()
                    lines = []
                    for i, p in enumerate(plants, 1):
                        last = p.get("last_watered", today)
                        days_since = (today - last).days
                        freq = p.get("watering_frequency_days", 2)
                        if days_since >= freq:
                            status = "💧 Water needed!"
                        else:
                            status = f"✅ Next water in {freq - days_since} day(s)"
                        lines.append(f"{i}. {p['name']} — {status}")
                    send_text(phone, "🌿 Your plants:\n\n" + "\n".join(lines))
                return jsonify(ok=True)

            # add plant Rose, 3 days  OR  add plant Tulsi, 2
            add_match = re.search(r"add plant (.+?),\s*(\d+)", text, re.IGNORECASE)
            if add_match:
                name = add_match.group(1).strip()
                days = int(add_match.group(2))
                add_plant(phone, name, days)
                send_text(phone, f"✅ Added {name} with a watering reminder every {days} day(s)!\n\nI'll remind you at 7:30 AM when it's time. 🌿")
                return jsonify(ok=True)

            remove_match = re.search(r"remove plant (.+)", text, re.IGNORECASE)
            if remove_match:
                name = remove_match.group(1).strip()
                removed = remove_plant(phone, name)
                if removed:
                    send_text(phone, f"🗑️ Removed {name} from your plant list.")
                else:
                    send_text(phone, f"Couldn't find '{name}'. Check 'my plants' to see your list.")
                return jsonify(ok=True)

        # ── Freemium gate — all AI features below ─────────────────────────
        allowed = check_freemium(user)
        if not allowed:
            return jsonify(ok=True)

        # ── Photo → plant health diagnosis ─────────────────────────────────
        if msg_type == "image":
            send_text(phone, "🔍 Analyzing your plant... give me a moment!")
            image_id = message["image"]["id"]
            media_resp = requests.get(
                f"https://graph.facebook.com/v18.0/{image_id}",
                headers={"Authorization": f"Bearer {os.getenv('META_ACCESS_TOKEN')}"},
            )
            image_url = media_resp.json().get("url")
            diagnosis = analyze_plant_photo(image_url)
            send_text(phone, f"🌿 Plant Health Report:\n\n{diagnosis}")
            return jsonify(ok=True)

        # ── Text AI intents ────────────────────────────────────────────────
        if msg_type == "text":
            text_lower = message["text"]["body"].strip().lower()

            weather_keywords = ["weather", "plant this", "season", "what to plant", "planting advice"]
            if any(kw in text_lower for kw in weather_keywords):
                send_text(phone, "🌤️ Checking this week's weather for you...")
                advice = get_weather_advice(
                    user.get("latitude", 28.6139),
                    user.get("longitude", 77.2090),
                    user.get("plants", []),
                )
                send_text(phone, f"🌱 Weather Planting Advice:\n\n{advice}")
                return jsonify(ok=True)

            # General plant question
            reply = answer_plant_question(message["text"]["body"], user.get("plants", []))
            send_text(phone, reply)

    except Exception as e:
        print(f"[Webhook Error] {e}")

    return jsonify(ok=True)


# ── Razorpay payment webhook ───────────────────────────────────────────────
@webhook_bp.post("/payment-webhook")
def payment_webhook():
    event = request.get_json(silent=True) or {}
    if event.get("event") == "payment.captured":
        notes = event.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
        phone = notes.get("phone")
        if phone:
            activate_premium(phone)
            send_text(phone, "🎉 Premium activated! You now have unlimited access to PlantCare Bot. Happy growing! 🌿")
    return jsonify(ok=True)
