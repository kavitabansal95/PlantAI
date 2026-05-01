import os
from models.user import can_use_bot, remaining_free, increment_count
from services.whatsapp import send_text, send_paywall


def check_freemium(user: dict) -> bool:
    """Returns True if user is allowed to use AI features, False if blocked."""
    limit = int(os.getenv("FREE_CONVERSATION_LIMIT", 20))

    if not can_use_bot(user):
        send_paywall(user["phone"], user.get("conversation_count", 0), limit)
        return False

    # Warn when close to limit
    remaining = remaining_free(user)
    if not user.get("is_premium") and 0 < remaining <= 3:
        send_text(
            user["phone"],
            f"⚠️ Heads up! You have {remaining} free conversation{'s' if remaining != 1 else ''} left.\n\n"
            f"Upgrade for ₹99/month to keep going: {os.getenv('PAYMENT_LINK')}",
        )

    increment_count(user["phone"])
    return True
