"""Explicit destinations for the private Telegram hub and website threads."""

SITES = ("flights", "hotels", "activities")
LABELS = {"flights": "Airside — flights", "hotels": "Staywell — hotels", "activities": "Daylight — activities"}

# This namespace is reserved at the website write boundary. Only the trusted
# Telegram controller can create these turns; their reply uses the normal bot
# reply path rather than a second mirrored notification.
TELEGRAM_REPLY_PREFIX = "telegram-reply-"


def is_telegram_reply(event_id):
    return isinstance(event_id, str) and event_id.startswith(TELEGRAM_REPLY_PREFIX)


def retire_confirmation_notifications(root):
    """Retire only unsent notices from the removed travel approval workflow."""
    import re
    from oneagent.app.notifications import (
        IN_FLIGHT, PENDING, RETRYABLE_FAILURE, fail_notification, notification_records,
    )
    for record in notification_records("telegram", root):
        if (record.status in {PENDING, IN_FLIGHT, RETRYABLE_FAILURE}
                and re.fullmatch(r"travel-mirror:[0-9a-f]{64}:confirmation", record.idempotency_key)):
            fail_notification("telegram", record.idempotency_key,
                              "Travel confirmation prompts have been removed.", root, terminal=True)
