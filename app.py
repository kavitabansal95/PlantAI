from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify
from webhook import webhook_bp
from services.scheduler import start_scheduler

app = Flask(__name__)
app.register_blueprint(webhook_bp)


@app.get("/")
def health():
    return jsonify(status="PlantCare Bot is running 🌱")


if __name__ == "__main__":
    import os
    start_scheduler()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
