"""Execute travel reasoning inside the normal bot's existing conversation."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from oneagent.app.epoch import require_current_daemon_epoch
from oneagent.collaboration.handoff import HandoffStore, digest
from oneagent.collaboration.store import encoded, identifier, object_value
from .agent import TravelResponder
from .domain import TripStore, travel_tools


def local_request(url, token, body, *, timeout=650):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username:
        raise ValueError("The bot bridge must use loopback HTTP")
    request = Request(url, data=encoded(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError):
        raise RuntimeError("The running Telegram bot is unavailable. Reconnect the bot, then retry this reply.") from None


def call_bot(route, body):
    chat_id, url, token = route
    return local_request(url, token, dict(body, chat_id=chat_id))


class BotTravelBridge(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, bot, travel_root):
        self.bot, self.travel_root = bot, Path(travel_root).resolve()
        self.handoffs = HandoffStore(self.travel_root / "handoffs.sqlite")
        self.trips = TripStore(self.travel_root / "trips.sqlite")
        self.tools = travel_tools(self.trips)
        self.token = secrets.token_hex(32)
        self.registration_stop = threading.Event()
        self.registration_thread = None
        self.db_path = self.travel_root / "bot-replies.sqlite"
        db = sqlite3.connect(self.db_path)
        try:
            db.execute("CREATE TABLE IF NOT EXISTS replies(owner TEXT, app TEXT, event TEXT, request TEXT, response TEXT, PRIMARY KEY(owner,app,event))")
            db.commit()
        finally:
            db.close()
        super().__init__(("127.0.0.1", 0), BotHandler)
        threading.Thread(target=self.serve_forever, daemon=True).start()

    def attach(self, config, chat_id):
        local_request(config["url"].removesuffix("/telegram") + "/attach", config["token"],
                      {"chat_id": chat_id, "url": f"http://127.0.0.1:{self.server_port}/respond", "token": self.token}, timeout=10)

    def maintain_registration(self, config_path):
        if self.registration_thread is not None:
            return
        def refresh():
            while not self.registration_stop.is_set():
                try:
                    config = json.loads(Path(config_path).expanduser().read_text())
                    with sqlite3.connect(self.travel_root / "visitors.sqlite") as db:
                        chats = [row[0] for row in db.execute("SELECT DISTINCT chat FROM bot_owners")]
                    for chat in chats:
                        if self.registration_stop.is_set():
                            break
                        if self.bot._chat_allowed(chat):
                            self.attach(config, chat)
                except (OSError, ValueError, RuntimeError, sqlite3.Error):
                    pass  # The backend may be restarting; the durable outbox waits.
                self.registration_stop.wait(5)
        self.registration_thread = threading.Thread(target=refresh, daemon=True, name="travel-bot-registration")
        self.registration_thread.start()

    def server_close(self):
        self.registration_stop.set()
        if self.registration_thread:
            self.registration_thread.join(timeout=11)
        super().server_close()

    def check_owner(self, owner, chat_id):
        require_current_daemon_epoch(self.bot.daemon_epoch, self.bot.root)
        if type(chat_id) is not int or chat_id <= 0 or not self.bot._chat_allowed(chat_id):
            raise PermissionError("This chat is not authorized")
        expected = self.handoffs.account(f"telegram:{chat_id}:{chat_id}", include_inactive=True)
        if owner != expected:
            raise PermissionError("This trip does not belong to the Telegram conversation")

    def respond(self, owner, chat_id, payload):
        self.check_owner(owner, chat_id)
        payload = object_value(payload)
        current = object_value(payload["current"])
        app, event = identifier(current["app_id"]), identifier(current["event_id"])
        request_hash = digest(encoded(current))
        session_key = self.bot._session_key(chat_id)
        with self.bot.conversation_lock(session_key):
            db = sqlite3.connect(self.db_path, timeout=20)
            try:
                row = db.execute("SELECT request,response FROM replies WHERE owner=? AND app=? AND event=?", (owner, app, event)).fetchone()
                if row:
                    if row[0] != request_hash:
                        raise ValueError("Conflicting travel event")
                    return json.loads(row[1])
                proposals = []
                respond = TravelResponder(owner, self.bot.root, self.trips, self.tools,
                    lambda _owner, _app, _event, value: proposals.append(value),
                    runtime=self.bot.runtime, identity=self.bot.identity, session_key=session_key,
                    conversation_lock=self.bot.conversation_lock(session_key), invoke=self.bot._invoke_runtime_response)
                answer = respond(payload, session_key)
                result = {"answer": answer, "proposal": proposals[-1] if proposals else None}
                with db:
                    db.execute("INSERT INTO replies VALUES (?,?,?,?,?)", (owner, app, event, request_hash, encoded(result)))
                return result
            finally:
                db.close()

    def notify(self, owner, chat_id, event, output):
        self.check_owner(owner, chat_id)
        if event.get("app_id") not in {"flights", "hotels", "activities"}:
            raise PermissionError("Only website-originated exchanges can be mirrored")
        app, event_id = event["app_id"], identifier(event["event_id"])
        if output.get("in_reply_to") != event["message"]["id"]:
            raise ValueError("Reply correlation mismatch")
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT request,response FROM replies WHERE owner=? AND app=? AND event=?", (owner, app, event_id)).fetchone()
        if not row or row[0] != digest(encoded(event)) or json.loads(row[1])["answer"]["text"] != output["text"]:
            raise PermissionError("This exchange has not been saved by the bot")
        selected = event.get("context", {}).get("selected_object", {})
        label = {"flights": "Airside", "hotels": "Staywell", "activities": "Daylight"}[app]
        if selected.get("name"):
            label += " · " + selected["name"] + (" " + selected["code"] if selected.get("code") else "")
        text = f"{label}\n\nYou: {event['message']['text']}\n\nOneAgent: {output['text']}"
        key = "travel-mirror:" + digest(f"{owner}:{app}:{event_id}")
        # Stable per-part IDs also protect long exchanges from partial-send retries.
        with self.bot._notification_order_lock:
            for index, start in enumerate(range(0, len(text), 3500)):
                result = self.bot.notifications.send(chat_id, text[start:start + 3500], idempotency_key=f"{key}:{index}")
                if not result.delivered:
                    return {"delivered": False, "terminal": result.terminal}
        return {"delivered": True}


class BotHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        status, result = 200, {}
        try:
            if self.path not in {"/respond", "/notify"} or not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.server.token):
                raise PermissionError("Unauthorized")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2_000_000:
                raise ValueError("Invalid request size")
            data = json.loads(self.rfile.read(size))
            result = (self.server.respond(data["owner"], data["chat_id"], data["payload"]) if self.path == "/respond" else
                      self.server.notify(data["owner"], data["chat_id"], data["event"], data["output"]))
        except PermissionError:
            status, result = 403, {"error": "Unauthorized"}
        except (ValueError, KeyError, TypeError):
            status, result = 400, {"error": "Invalid travel request"}
        except Exception:
            status, result = 503, {"error": "The bot could not complete this turn"}
        data = encoded(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
