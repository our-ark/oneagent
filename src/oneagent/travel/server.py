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
from urllib.parse import parse_qs, urlsplit

from oneagent.collaboration import AgentState, AppClient, AppServer, CollaborationService
from oneagent.collaboration.store import encoded, identifier, object_value
from .agent import TravelResponder
from .domain import CATALOG, TravelMessageStore, TripStore, item, travel_tools

LOG = logging.getLogger(__name__)
APPS = ("home", "flights", "hotels")


class Hub:
    def __init__(self, root, *, responder_factory=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db_path = self.root / "visitors.sqlite"
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS visitors(owner TEXT PRIMARY KEY, csrf TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS proposals(owner TEXT, app TEXT, event TEXT, body TEXT, PRIMARY KEY(owner,app,event));
                """)
        finally:
            db.close()
        self.trips = TripStore(self.root / "trips.sqlite")
        self.tools = travel_tools(self.trips)
        self.stores, self.servers = {}, {}
        self.lock = threading.RLock()
        self.visitors = {}
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="oneagent-travel")
        self.responder_factory = responder_factory
        for app_id in APPS:
            store = TravelMessageStore(self.root / f"{app_id}.sqlite", app_id, shared_fields=["budget_cents", "preferences"])
            server = AppServer(("127.0.0.1", 0), store, {secrets.token_hex(32): "bootstrap"})
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.stores[app_id], self.servers[app_id] = store, server

    def close(self):
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
                respond = (self.responder_factory(owner) if self.responder_factory else
                           TravelResponder(owner, runtime_root, self.trips, self.tools, self.set_proposal))
                service = CollaborationService(apps, AgentState(runtime_root / "journal.sqlite", owner), respond)
                self.visitors[owner] = {"service": service, "running": False, "dirty": False, "error": None}
            return self.visitors[owner]

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

    def set_proposal(self, owner, app, event, proposal):
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                db.execute("INSERT INTO proposals VALUES (?,?,?,?) ON CONFLICT(owner,app,event) DO UPDATE SET body=excluded.body", (owner, app, event, encoded(proposal)))
        finally:
            db.close()

    def transcript(self, owner, app, session):
        transcript = self.stores[app].transcript(owner, session)
        db = sqlite3.connect(self.db_path)
        try:
            for output in transcript["outputs"]:
                row = db.execute("SELECT body FROM proposals WHERE owner=? AND app=? AND event=?", (owner, app, output["in_reply_to"])).fetchone()
                if row:
                    output["proposal"] = json.loads(row[0])
        finally:
            db.close()
        with self.lock:
            # Resume queued messages after a server restart when this session reopens.
            completed = {output["in_reply_to"] for output in transcript["outputs"]}
            if owner not in self.visitors and any(message["message"]["id"] not in completed for message in transcript["messages"]):
                self.kick(owner)
            state = self.visitors.get(owner, {})
            transcript.update(running=state.get("running", False), error=state.get("error"))
        return transcript


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, hub, web_root, public_origin=None):
        self.hub, self.web_root = hub, Path(web_root).resolve()
        super().__init__(address, WebHandler)
        self.public_origin = public_origin or f"http://127.0.0.1:{self.server_port}"


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
                result = {"visitor": owner, "csrf": csrf, "trip": hub.trips.get(owner), "catalog": CATALOG, "mode": "test-fixture" if hub.responder_factory else "live"}
            elif write and url.path == "/api/sessions":
                app = self.app(body["app_id"])
                result = hub.stores[app].session(owner)
            elif write and url.path == "/api/messages":
                app = self.app(body["app_id"])
                result = hub.stores[app].message(owner, body)
                hub.kick(owner)
            elif not write and url.path == "/api/transcript":
                result = hub.transcript(owner, self.app(query["app_id"][0]), query["session_id"][0])
            elif not write and url.path == "/api/trip":
                result = hub.trips.get(owner)
            elif write and url.path == "/api/preferences":
                result = hub.trips.update(owner, {"budget_cents": body["budget_cents"], "preferences": body["preferences"]}, identifier(body["id"]))
            elif write and url.path == "/api/action":
                kind = body.get("kind")
                if kind not in {"flight", "hotel", "brief"}:
                    raise ValueError("Invalid action")
                name, args = (("trip.update_brief", object_value(body.get("changes"))) if kind == "brief" else ("trip.save_" + kind, {"id": body.get("item_id")}))
                result = hub.tools.invoke(name, args, owner=owner, request_id=identifier(body["id"]),
                                          authorize=lambda who, tool, values: who == owner and tool == name and values == args)
            elif write and url.path == "/api/retry":
                hub.kick(owner)
                result = {"queued": True}
            elif write and url.path == "/api/new-trip":
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

    @staticmethod
    def app(app_id):
        if app_id not in APPS:
            raise ValueError("Unknown app")
        return app_id

    def headers_for(self, status, mime, size):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if self.new_cookie:
            secure = "; Secure" if self.server.public_origin.startswith("https://") else ""
            self.send_header("Set-Cookie", f"oneagent_visit={self.new_cookie}; HttpOnly; SameSite=Lax; Path=/{secure}")
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
        if route in {"/", "/home", "/flights", "/hotels"}:
            path = root / "index.html"
        if not path.is_file():
            self.send_json(404, {"error": "File not found. Build the web app first."})
            return
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.headers_for(200, mime, len(data))
        self.wfile.write(data)
