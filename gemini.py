import google.generativeai as genai
import requests
import os
import base64

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def analyze_plant_photo(image_url: str) -> str:
    """Download image from Meta CDN and send to Gemini Vision."""
    headers = {"Authorization": f"Bearer {os.getenv('META_ACCESS_TOKEN')}"}
    resp = requests.get(image_url, headers=headers)
    resp.raise_for_status()

    image_data = base64.b64encode(resp.content).decode("utf-8")
    mime_type = resp.headers.get("content-type", "image/jpeg")

    prompt = """You are a plant care expert. Analyze this plant photo carefully and respond in a friendly, WhatsApp-friendly format (short paragraphs, no markdown symbols).

Please provide:
1. Plant identification (if possible)
2. Health status (Healthy / Needs attention / Critical)
3. What you observe (diseases, pests, yellowing, overwatering, underwatering, etc.)
4. 3 specific actionable care tips
5. One encouragement line

Keep it concise and warm. Use simple language. Max 200 words."""

    image_part = {"mime_type": mime_type, "data": image_data}
    response = model.generate_content([prompt, image_part])
    return response.text


def get_weather_advice(latitude: float, longitude: float, plants: list) -> str:
    """Fetch Open-Meteo weather (free, no key) and ask Gemini for planting advice."""
    weather_resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "forecast_days": 7,
            "timezone": "Asia/Kolkata",
        },
    )
    weather_resp.raise_for_status()
    daily = weather_resp.json()["daily"]

    avg_max = sum(daily["temperature_2m_max"]) / 7
    avg_min = sum(daily["temperature_2m_min"]) / 7
    total_rain = sum(daily["precipitation_sum"])

    plant_list = ", ".join(p["name"] for p in plants) if plants else "no plants registered yet"

    prompt = f"""You are a plant care expert for Indian gardens.

Weather this week: Avg high {avg_max:.1f}C, avg low {avg_min:.1f}C, total rainfall {total_rain:.1f}mm.
User's current plants: {plant_list}

Based on this weather, give WhatsApp-friendly advice (no markdown, short paragraphs):
1. Which 2-3 plants are GREAT to plant right now in this weather
2. Which plants (if any from their list) might struggle and what to do
3. One seasonal gardening tip

Keep it practical, specific, and friendly. Max 180 words."""

    response = model.generate_content(prompt)
    return response.text


def answer_plant_question(question: str, plants: list) -> str:
    """Answer a general plant question with user's plant context."""
    if plants:
        plant_context = f"The user has these plants: {', '.join(f'{p[\"name\"]} (watered every {p[\"watering_frequency_days\"]} days)' for p in plants)}."
    else:
        plant_context = "The user has no plants registered yet."

    prompt = f"""You are a friendly plant care expert on WhatsApp. {plant_context}

User asks: "{question}"

Reply in a warm, conversational WhatsApp style. No markdown formatting. Keep it under 150 words. Be practical and specific."""

    response = model.generate_content(prompt)
    return response.text
