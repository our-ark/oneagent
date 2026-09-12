"""Travel mode and authenticated bridge for the normal OneAgent Telegram bot."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib.request import Request, urlopen

from oneagent.collaboration.handoff import digest
from oneagent.collaboration.store import encoded
from .routing import LABELS, SITES, TELEGRAM_REPLY_PREFIX


class TelegramDemo:
    """Call only after authenticating a private Telegram message's sender."""
    def __init__(self, hub):
        self.hub = hub
        self.lock = threading.RLock()
        with hub.handoffs.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS telegram_receipts(principal TEXT, event TEXT, text TEXT, reply TEXT, PRIMARY KEY(principal,event))")

    def handle(self, chat_id, user_id, message_id, text):
        if type(chat_id) is not int or chat_id <= 0 or chat_id != user_id:
            return None  # Private chats only: never share a group's identity.
        if not isinstance(text, str) or not text.strip() or len(text) > 16000:
            return None
        principal = f"telegram:{chat_id}:{user_id}"
        command = text.split()[0].split("@")[0].lower()
        owner = self.hub.handoffs.account(principal)
        if command != "/traveldemo" and (not owner or command.startswith("/")):
            return None
        key = digest(principal)
        event = str(message_id)
        with self.lock:
            with self.hub.handoffs.connect() as db:
                cached = db.execute("SELECT text,reply FROM telegram_receipts WHERE principal=? AND event=?", (key, event)).fetchone()
            if cached:
                if cached[0] != text:
                    raise ValueError("Conflicting Telegram message ID")
                return cached[1]
            if command == "/traveldemo":
                arguments = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) == 2 else ""
                action = arguments.lower()
                if action == "stop":
                    self.hub.handoffs.stop(principal)
                    reply = "Travel demo mode is off in Telegram. Our conversation stays with me; /traveldemo resumes the demo and /traveldemo reset starts fresh website chats."
                elif action in {"", "reset"}:
                    owner = self.hub.handoffs.account(principal, start=True, reset=action == "reset")
                    with sqlite3.connect(self.hub.db_path) as db:
                        registered = db.execute("SELECT 1 FROM bot_routes WHERE chat=?", (chat_id,)).fetchone()
                    if registered:
                        self.hub.bind_owner(owner, chat_id)
                    links = self.hub.links(owner)
                    reply = ("Travel demo mode is on. We’re planning Tokyo, Nov 6–9, 2026. Tell me your budget and preferences here, then open any site:\n\n"
                             + "\n\n".join(f"{LABELS[app]}\n{url}" for app, url in links.items()))
                elif action.split(maxsplit=1)[0] == "reply":
                    parts = arguments.split(maxsplit=2)
                    if len(parts) != 3 or parts[1].lower() not in SITES:
                        reply = "Use /traveldemo reply <flights|hotels|activities> <request>. Only the chosen website will receive that request and my answer."
                    elif not owner:
                        reply = "Send /traveldemo first to resume your demo, then send your website request."
                    else:
                        app = parts[1].lower()
                        reply = f"Sent to {LABELS[app]} only.\n\n" + self.reply(owner, app, TELEGRAM_REPLY_PREFIX + str(message_id), parts[2])
                else:
                    reply = "Use /traveldemo for links, /traveldemo reply <flights|hotels|activities> <request> for a website reply, /traveldemo reset for fresh website chats, or /traveldemo stop to leave demo mode."
            else:
                reply = self.reply(owner, "telegram", f"tg-{message_id}", text)
            # Persist before network delivery so transport retries never run a
            # model or reset a trip twice. This private outbox contains links.
            with self.hub.handoffs.connect() as db:
                db.execute("INSERT INTO telegram_receipts VALUES (?,?,?,?)", (key, event, text, reply))
            return reply

    def reply(self, owner, app, event_id, text):
        session = self.hub.channel(owner, app)
        self.hub.submit(owner, app, {"id": event_id, "session_id": session, "text": text, "context": {}})
        deadline = time.monotonic() + 610
        while time.monotonic() < deadline:
            transcript = self.hub.transcript(owner, app, session)
            output = next((o for o in transcript["outputs"] if o["in_reply_to"] == event_id), None)
            if output:
                reply = output["text"]
                return reply
            if transcript["error"]:
                raise RuntimeError(transcript["error"])
            time.sleep(.1)
        raise RuntimeError("The travel agent is still processing. Retry this message shortly.")


def connect_existing_bot(application, config_path):
    from .bot_bridge import BotTravelBridge
    config = json.loads(Path(config_path).expanduser().read_text())
    if application._travel_bridge is None:
        application._travel_bridge = BotTravelBridge(application, config["root"])
    elif application._travel_bridge.travel_root != Path(config["root"]).resolve():
        raise ValueError("Restart the bot after changing the travel workspace")
    application._travel_bridge.maintain_registration(config_path)
    return config, application._travel_bridge


def existing_bot_reply(event, root, *, application=None):
    """Opt-in bridge for the existing OneAgent Telegram daemon (one poller)."""
    config_path = os.environ.get("ONEAGENT_TRAVEL_CONTROL_FILE")
    if not config_path:
        return None
    command = event.text.strip().split(maxsplit=1)[0].split("@")[0].lower() if event.text.strip() else ""
    if command.startswith("/") and command != "/traveldemo":
        return None
    message = event.raw.get("message", {})
    chat, sender = message.get("chat", {}), message.get("from", {})
    if chat.get("type") != "private" or sender.get("is_bot") or sender.get("id") != chat.get("id"):
        return None
    try:
        config = json.loads(Path(config_path).expanduser().read_text())
        if command != "/traveldemo" and config.get("root"):
            from oneagent.collaboration.handoff import HandoffStore
            active = HandoffStore(Path(config["root"]) / "handoffs.sqlite").account(f"telegram:{chat['id']}:{sender['id']}")
            if not active:
                return None
        if application is not None:
            config, bridge = connect_existing_bot(application, config_path)
            bridge.attach(config, chat["id"])
        request = Request(config["url"], data=encoded({"chat_id": chat["id"], "user_id": sender["id"], "message_id": event.message_id, "text": event.text}).encode(),
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + config["token"]})
        with urlopen(request, timeout=650) as response:
            return json.load(response).get("reply")
    except (OSError, ValueError, KeyError, RuntimeError):
        return "The travel demo service is unavailable. Start bin/oneagent-travel and try again."
