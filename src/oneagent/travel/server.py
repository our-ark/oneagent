"""Local demo gateway; app message feeds remain separate HTTP services."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import mimetypes
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.parse import parse_qs, urlsplit

from oneagent.collaboration import AgentState, AppClient, AppServer, CollaborationService
from oneagent.collaboration.handoff import HandoffStore
from oneagent.collaboration.store import encoded, identifier, object_value
from .agent import TravelResponder
from .domain import CATALOG, TravelMessageStore, travel_tools
from .routing import SITES, is_telegram_reply

LOG = logging.getLogger(__name__)
APPS = ("home", *SITES, "telegram")


class Hub:
    def __init__(self, root, *, responder_factory=None, mirror_worker=True):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db_path = self.root / "visitors.sqlite"
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS visitors(owner TEXT PRIMARY KEY, csrf TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS timeline(seq INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT, app TEXT, event TEXT, UNIQUE(owner,app,event));
                    CREATE TABLE IF NOT EXISTS bot_routes(chat INTEGER PRIMARY KEY, url TEXT, token TEXT);
                    CREATE TABLE IF NOT EXISTS bot_owners(owner TEXT PRIMARY KEY, chat INTEGER);
                    CREATE TABLE IF NOT EXISTS mirror_outbox(owner TEXT, app TEXT, event TEXT, body TEXT, status TEXT DEFAULT 'pending', next_attempt REAL DEFAULT 0, PRIMARY KEY(owner,app,event));
                    CREATE TABLE IF NOT EXISTS website_chat_resets(owner TEXT, app TEXT, cursor INTEGER NOT NULL, PRIMARY KEY(owner,app));
                """)
        finally:
            db.close()
        self.handoffs = HandoffStore(self.root / "handoffs.sqlite")
        self.origins = {}
        self.tools = travel_tools()
        self.stores, self.servers = {}, {}
        self.lock = threading.RLock()
        self.visitors = {}
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="oneagent-travel")
        self.responder_factory = responder_factory
        for app_id in APPS:
            store = TravelMessageStore(self.root / f"{app_id}.sqlite", app_id,
                                      shared_fields=[])
            server = AppServer(("127.0.0.1", 0), store, {secrets.token_hex(32): "bootstrap"})
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.stores[app_id], self.servers[app_id] = store, server
        self.clear_website_chats()
        self.mirror_stop = threading.Event()
        self.mirror_thread = None
        if mirror_worker:
            self.mirror_thread = threading.Thread(target=self._mirror_loop, daemon=True, name="travel-notifications")
            self.mirror_thread.start()

    def close(self):
        self.mirror_stop.set()
        if self.mirror_thread:
            self.mirror_thread.join(timeout=12)
        self.executor.shutdown(wait=True)
        for server in self.servers.values():
            server.shutdown()
            server.server_close()

    def identity(self, cookie):
        try:
            cookies = SimpleCookie(cookie)
            token = cookies["oneagent_visit"].value if "oneagent_visit" in cookies else ""
        except Exception:
            token = ""
        owner = hashlib.sha256(token.encode()).hexdigest() if len(token) == 64 else ""
        db = sqlite3.connect(self.db_path)
        try:
            row = db.execute("SELECT csrf FROM visitors WHERE owner=?", (owner,)).fetchone()
            if row:
                return owner, row[0], None
            token = secrets.token_hex(32)
            owner, csrf = hashlib.sha256(token.encode()).hexdigest(), secrets.token_hex(32)
            with db:
                db.execute("INSERT INTO visitors VALUES (?,?)", (owner, csrf))
            return owner, csrf, token
        finally:
            db.close()

    def worker(self, owner):
        with self.lock:
            if owner not in self.visitors:
                apps = []
                for app_id, server in self.servers.items():
                    token = secrets.token_hex(32)
                    server.tokens[token] = owner
                    apps.append(AppClient(app_id, f"http://127.0.0.1:{server.server_port}", token))
                runtime_root = self.root / "agents" / owner
                runtime_root.mkdir(parents=True, exist_ok=True, mode=0o700)
                respond = self.responder_factory(owner) if self.responder_factory else self.responder(owner, runtime_root)
                service = CollaborationService(apps, AgentState(runtime_root / "journal.sqlite", owner), respond,
                    on_output=lambda app, event, output: self.queue_mirror(owner, app, event, output))
                self.visitors[owner] = {"service": service, "running": False, "dirty": False, "error": None}
            return self.visitors[owner]

    def bind_bot(self, chat_id, url, token):
        parsed = urlsplit(url)
        if type(chat_id) is not int or chat_id <= 0 or parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/respond" or parsed.username or len(token) != 64:
            raise ValueError("Invalid local bot binding")
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                previous = db.execute("SELECT url,token FROM bot_routes WHERE chat=?", (chat_id,)).fetchone()
                db.execute("INSERT INTO bot_routes VALUES (?,?,?) ON CONFLICT(chat) DO UPDATE SET url=excluded.url,token=excluded.token", (chat_id, url, token))
        finally:
            db.close()
        owner = self.handoffs.account(f"telegram:{chat_id}:{chat_id}", include_inactive=True)
        if owner:
            self.bind_owner(owner, chat_id)
            if previous is not None and previous != (url, token):
                self.clear_website_chats(owner)
            # Resume the saved output/cursor transaction after either process
            # restarts, even when the browser has not reopened the conversation.
            if previous != (url, token) or owner not in self.visitors:
                self.kick(owner)

    def clear_website_chats(self, owner=None):
        """Start fresh visible threads without losing private memory or delivery receipts."""
        with sqlite3.connect(self.db_path) as db:
            for app in SITES:
                with self.stores[app].connect() as store:
                    if owner is None:
                        cursor = store.execute("SELECT COALESCE(MAX(cursor),0) FROM events").fetchone()[0]
                    else:
                        cursor = store.execute("SELECT COALESCE(MAX(cursor),0) FROM events WHERE owner=?", (owner,)).fetchone()[0]
                db.execute("INSERT INTO website_chat_resets VALUES (?,?,?) ON CONFLICT(owner,app) DO UPDATE SET cursor=MAX(cursor,excluded.cursor)", (owner or "", app, cursor))

    def website_chat_cursor(self, owner, app):
        with sqlite3.connect(self.db_path) as db:
            return db.execute("SELECT COALESCE(MAX(cursor),0) FROM website_chat_resets WHERE app=? AND owner IN ('',?)", (app, owner)).fetchone()[0]

    def bind_owner(self, owner, chat_id):
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                db.execute("INSERT INTO bot_owners VALUES (?,?) ON CONFLICT(owner) DO UPDATE SET chat=excluded.chat", (owner, chat_id))
        finally:
            db.close()

    def bot_route(self, owner):
        db = sqlite3.connect(self.db_path)
        try:
            row = db.execute("SELECT b.chat,r.url,r.token FROM bot_owners b LEFT JOIN bot_routes r ON r.chat=b.chat WHERE b.owner=?", (owner,)).fetchone()
            return row
        finally:
            db.close()

    def responder(self, owner, runtime_root):
        local = None
        def respond(payload, key):
            nonlocal local
            route = self.bot_route(owner)
            if route and route[1]:
                from .bot_bridge import call_bot
                result = call_bot(route, {"owner": owner, "payload": payload})
                return result["answer"]
            if route:
                raise RuntimeError("The Telegram bot is not attached. Start the normal bot with the travel control file.")
            if local is None:
                local = TravelResponder(owner, runtime_root, self.tools)
            return local(payload, key)
        return respond

    def queue_mirror(self, owner, app, event, output):
        if app not in SITES or is_telegram_reply(event["event_id"]) or not self.bot_route(owner):
            return
        body = encoded({"owner": owner, "event": event, "output": output})
        db = sqlite3.connect(self.db_path, timeout=20)
        try:
            with db:
                db.execute("INSERT OR IGNORE INTO mirror_outbox(owner,app,event,body) VALUES (?,?,?,?)", (owner, app, event["event_id"], body))
        finally:
            db.close()

    def deliver_mirrors(self):
        from .bot_bridge import local_request
        db = sqlite3.connect(self.db_path, timeout=20)
        try:
            rows = db.execute("SELECT owner,app,event,body FROM mirror_outbox WHERE status='pending' AND next_attempt<=? ORDER BY rowid LIMIT 20", (time.time(),)).fetchall()
            for owner, app, event, body in rows:
                route = self.bot_route(owner)
                if not route or not route[1]:
                    continue
                try:
                    result = local_request(route[1].removesuffix("/respond") + "/notify", route[2], dict(json.loads(body), chat_id=route[0]), timeout=10)
                    status = "delivered" if result["delivered"] else "failed" if result.get("terminal") else "pending"
                except (OSError, ValueError, RuntimeError):
                    status = "pending"
                with db:
                    db.execute("UPDATE mirror_outbox SET status=?,next_attempt=? WHERE owner=? AND app=? AND event=?", (status, time.time() + 15, owner, app, event))
        finally:
            db.close()

    def _mirror_loop(self):
        while not self.mirror_stop.wait(2):
            try:
                self.deliver_mirrors()
            except Exception:
                LOG.exception("Website replies are saved; Telegram mirroring will retry")

    def kick(self, owner):
        with self.lock:
            state = self.worker(owner)
            state["dirty"] = True
            if not state["running"]:
                state["running"], state["error"] = True, None
                self.executor.submit(self._run, owner)

    def _run(self, owner):
        state = self.worker(owner)
        try:
            while True:
                with self.lock:
                    state["dirty"] = False
                processed = state["service"].process_once()
                with self.lock:
                    if not processed and not state["dirty"]:
                        state["running"] = False
                        return
        except Exception:
            LOG.exception("Travel agent turn failed")
            with self.lock:
                state["running"] = False
                state["error"] = "OneAgent couldn't finish this reply. Check the runtime connection, then retry."

    def channel(self, owner, app):
        return self.handoffs.channel(owner, app, lambda: self.stores[app].session(owner))

    def submit(self, owner, app, body):
        result = self.stores[app].message(owner, body)
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                db.execute("INSERT OR IGNORE INTO timeline(owner,app,event) VALUES (?,?,?)", (owner, app, result["event_id"]))
        finally:
            db.close()
        self.kick(owner)
        return result

    def links(self, owner):
        # Fragments are not sent to web servers, previews, or referrers. The
        # browser exchanges the one-use token via an origin-checked POST.
        return {app: origin + "/#connect=" + self.handoffs.issue(owner, app)
                for app, origin in self.origins.items()}

    def conversation(self, owner, app=None):
        """A website gets only its own thread; the aggregate is private to the hub."""
        if app is not None:
            if app not in SITES:
                raise ValueError("Unknown website")
            transcript = self.transcript(owner, app, self.channel(owner, app), visible_only=True)
            return dict(transcript,
                messages=[dict(event, source_app=app,
                               origin="telegram" if is_telegram_reply(event["event_id"]) else app)
                          for event in transcript["messages"]],
                outputs=[dict(output, source_app=app) for output in transcript["outputs"]])
        db = sqlite3.connect(self.db_path)
        try:
            order = {(app, event): seq for seq, app, event in db.execute(
                "SELECT seq,app,event FROM timeline WHERE owner=? ORDER BY seq", (owner,))}
        finally:
            db.close()
        messages, outputs = [], []
        for app in APPS:
            transcript = self.transcript(owner, app, self.channel(owner, app))
            for event in transcript["messages"]:
                messages.append(dict(event, source_app=app, order=order.get((app, event["event_id"]), 0)))
            outputs.extend(dict(output, source_app=app) for output in transcript["outputs"])
        messages.sort(key=lambda event: event["order"])
        with self.lock:
            state = self.visitors.get(owner, {})
            return dict(messages=messages, outputs=outputs, running=state.get("running", False), error=state.get("error"))

    def transcript(self, owner, app, session, *, visible_only=False):
        transcript = self.stores[app].transcript(owner, session)
        if visible_only:
            cutoff = self.website_chat_cursor(owner, app)
            with self.stores[app].connect() as store:
                visible = {row[0] for row in store.execute("SELECT id FROM events WHERE owner=? AND session=? AND cursor>?", (owner, session, cutoff))}
            transcript["messages"] = [event for event in transcript["messages"] if event["event_id"] in visible]
            transcript["outputs"] = [output for output in transcript["outputs"] if output["in_reply_to"] in visible]
        with self.lock:
            # Resume queued messages after a server restart when this session reopens.
            completed = {output["in_reply_to"] for output in transcript["outputs"]}
            pending = any(message["message"]["id"] not in completed for message in transcript["messages"])
            if owner not in self.visitors and pending:
                self.kick(owner)
            state = self.visitors.get(owner, {})
            transcript.update(running=pending and state.get("running", False), error=state.get("error") if pending else None)
        return transcript


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, hub, web_root, public_origin=None, *, app_id=None):
        self.hub, self.web_root = hub, Path(web_root).resolve()
        if app_id is not None and app_id not in SITES:
            raise ValueError("Unknown website")
        self.app_id = app_id
        self.cookie_name = f"oneagent_{app_id}" if app_id else "oneagent_visit"
        super().__init__(address, WebHandler)
        self.public_origin = public_origin or f"http://127.0.0.1:{self.server_port}"
        parsed = urlsplit(self.public_origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            self.server_close()
            raise ValueError("Public origin must be an exact http(s) origin without a path")
        if app_id:
            hub.origins[app_id] = self.public_origin


class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, write):
        self.new_cookie = None
        try:
            url = urlsplit(self.path)
            if not url.path.startswith("/api/"):
                if write:
                    self.send_json(405, {"error": "Method not allowed"})
                else:
                    self.static(url.path)
                return
            hub = self.server.hub
            if self.server.app_id:
                try:
                    cookies = SimpleCookie(self.headers.get("Cookie", ""))
                    token = cookies[self.server.cookie_name].value if self.server.cookie_name in cookies else ""
                except Exception:
                    token = ""
                owner, csrf, self.new_cookie = hub.handoffs.browser(token, self.server.app_id, allow_new=url.path == "/api/session")
            else:
                owner, csrf, self.new_cookie = hub.identity(self.headers.get("Cookie", ""))
            body = {}
            if write:
                if self.headers.get("Origin") != self.server.public_origin or not secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), csrf):
                    raise PermissionError("Invalid browser session; reload the page")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 32000:
                    raise ValueError("Invalid request size")
                body = object_value(json.loads(self.rfile.read(size)))
            query = parse_qs(url.query)
            if not write and url.path == "/api/session":
                site = self.server.app_id
                result = {"csrf": csrf,
                          "catalog": {site: CATALOG[site]} if site else CATALOG,
                          "app_id": site, "linked": hub.handoffs.linked(owner),
                          "session_id": hub.channel(owner, site) if site else None,
                          "mode": "test-fixture" if hub.responder_factory else "live"}
                if not site:
                    result.update(visitor=owner, origins=hub.origins)
            elif write and url.path == "/api/connect" and self.server.app_id:
                owner, csrf, self.new_cookie = hub.handoffs.redeem(body.get("token"), self.server.app_id)
                result = {"connected": True}
            elif write and url.path == "/api/links":
                result = hub.links(owner)
            elif not write and url.path == "/api/conversation":
                result = hub.conversation(owner, self.server.app_id)
            elif write and url.path == "/api/sessions":
                app = self.app(body["app_id"])
                result = {"session_id": hub.channel(owner, app)} if self.server.app_id else hub.stores[app].session(owner)
            elif write and url.path == "/api/messages":
                app = self.app(body["app_id"])
                if is_telegram_reply(body.get("id")):
                    raise PermissionError("This message ID is reserved for explicit Telegram replies")
                result = hub.submit(owner, app, body)
            elif not write and url.path == "/api/transcript":
                result = hub.transcript(owner, self.app(query["app_id"][0]), query["session_id"][0], visible_only=bool(self.server.app_id))
            elif write and url.path == "/api/retry":
                hub.kick(owner)
                result = {"queued": True}
            elif write and url.path == "/api/new-trip":
                if self.server.app_id:
                    raise ValueError("Use /traveldemo reset in Telegram to start fresh website chats.")
                # Start a new visitor identity; existing histories remain private in their own workspace.
                _, _, self.new_cookie = hub.identity("")
                result = {"reset": True}
            else:
                self.send_json(404, {"error": "Not found"})
                return
            self.send_json(200, result)
        except PermissionError as error:
            self.send_json(403, {"error": str(error)})
        except (ValueError, KeyError, TypeError) as error:
            self.send_json(400, {"error": str(error) if isinstance(error, ValueError) else "Invalid request"})
        except Exception:
            LOG.exception("Travel request failed")
            self.send_json(500, {"error": "Something went wrong. Please try again."})

    def app(self, app_id):
        if app_id not in APPS:
            raise ValueError("Unknown app")
        if self.server.app_id and app_id != self.server.app_id:
            raise PermissionError("This website cannot write to another application's feed")
        return app_id

    def headers_for(self, status, mime, size):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if self.new_cookie:
            secure = "; Secure" if self.server.public_origin.startswith("https://") else ""
            self.send_header("Set-Cookie", f"{self.server.cookie_name}={self.new_cookie}; HttpOnly; SameSite=Lax; Path=/{secure}")
        self.end_headers()

    def send_json(self, status, body):
        data = encoded(body).encode()
        self.headers_for(status, "application/json", len(data))
        self.wfile.write(data)

    def static(self, route):
        root = self.server.web_root
        path = (root / route.lstrip("/")).resolve()
        if not path.is_relative_to(root):
            raise PermissionError("Invalid path")
        if route == "/":
            path = root / self.server.app_id / "index.html" if self.server.app_id else root / "index.html"
        elif self.server.app_id and (route.endswith(".html") or route.rstrip("/") in {"/home", "/flights", "/hotels", "/activities"}):
            self.send_json(404, {"error": "This is an independent website. Open the other site using your Telegram links."})
            return
        elif not self.server.app_id and route in {"/home", "/flights", "/hotels"}:
            path = root / "index.html"
        if not path.is_file():
            self.send_json(404, {"error": "File not found. Build the web app first."})
            return
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.headers_for(200, mime, len(data))
        self.wfile.write(data)
