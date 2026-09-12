"""Explicit destinations for the private Telegram hub and website threads."""

SITES = ("flights", "hotels", "activities")
LABELS = {"flights": "Airside — flights", "hotels": "Staywell — hotels", "activities": "Daylight — activities"}

# This namespace is reserved at the website write boundary. Only the trusted
# Telegram controller can create these turns; their reply uses the normal bot
# reply path rather than a second mirrored notification.
TELEGRAM_REPLY_PREFIX = "telegram-reply-"


def is_telegram_reply(event_id):
    return isinstance(event_id, str) and event_id.startswith(TELEGRAM_REPLY_PREFIX)


def confirmation_command(app, event_id):
    return f"/travelconfirm {event_id}" if app == "telegram" else f"/travelconfirm {app} {event_id}"
