import requests
import os

BASE_URL = f"https://graph.facebook.com/v18.0/{os.getenv('META_PHONE_NUMBER_ID')}/messages"


def _headers():
    return {
        "Authorization": f"Bearer {os.getenv('META_ACCESS_TOKEN')}",
        "Content-Type": "application/json",
    }


def send_text(to: str, message: str):
    requests.post(
        BASE_URL,
        json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}},
        headers=_headers(),
    )


def send_welcome(to: str, name: str = "Friend"):
    send_text(to, f"""🌿 Welcome to PlantCare Bot, {name}!

I can help you:
📸 Diagnose plant health from photos
🌤️ Get weather-based planting advice
💧 Get watering reminders

Try these commands:
• Send a plant photo → health diagnosis
• "weather advice" → what to plant this week
• "add plant Rose, 3 days" → track watering
• "my plants" → see your plant list
• "stop reminders" / "start reminders"

You have 20 free conversations. Let's grow! 🌱""")


def send_paywall(to: str, used: int, limit: int):
    send_text(to, f"""🌱 You've used {used}/{limit} free conversations!

To keep getting plant health diagnoses, weather advice, and watering reminders, upgrade to Premium.

✅ Unlimited plant photo analysis
✅ Daily weather-based tips
✅ Smart watering reminders
✅ Unlimited questions

💰 Only ₹99/month

👇 Pay here to continue:
{os.getenv('PAYMENT_LINK')}

After payment, send: PAID to activate instantly.""")
