"""Small outbound HTTP adapter; app credentials are scoped to one account."""
from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .store import encoded, identifier, object_value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class AppClient:
    app_id: str
    base_url: str
    token: str = field(repr=False)
    timeout: float = 15

    def __post_init__(self):
        identifier(self.app_id)
        url = urlsplit(self.base_url)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("App URL must not contain credentials, query, or fragment")
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}):
            raise ValueError("HTTPS required outside loopback")
        if not url.hostname:
            raise ValueError("App URL requires a host")
        self.base_url = self.base_url.rstrip("/")

    def request(self, path, body=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Expected an app-relative path")
        request = Request(self.base_url + path, data=encoded(body).encode() if body is not None else None,
                          headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        try:
            with build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                data = response.read(1000001)
                if len(data) > 1000000:
                    raise ValueError("App response too large")
                return object_value(json.loads(data))
        except HTTPError as error:
            raise ConnectionError(f"App {self.app_id} returned HTTP {error.code}") from None

    def events(self, after=0):
        batch = self.request(f"/collaboration/events?after={after}")
        if not isinstance(batch.get("events"), list):
            raise ValueError("Invalid event batch")
        cursor = after
        for event in batch["events"]:
            if event.get("app_id") != self.app_id or type(event.get("cursor")) is not int or event["cursor"] <= cursor:
                raise ValueError("Invalid event identity or cursor")
            cursor = event["cursor"]
            identifier(event.get("event_id"))
            identifier(event.get("session_id"))
            object_value(event.get("context"))
        return batch

    def output(self, session, body):
        return self.request("/collaboration/sessions/" + quote(session, safe="") + "/outputs", body)


class AppServer(ThreadingHTTPServer):
    """Headless reference server. Put behind HTTPS for non-local use.

    tokens maps bearer credentials to authenticated account IDs. Browser login,
    user messages and UI rendering belong to the application's own backend.
    """
    daemon_threads = True

    def __init__(self, address, store, tokens):
        self.store, self.tokens = store, dict(tokens)
        if not self.tokens or any(not token or not owner for token, owner in self.tokens.items()):
            raise ValueError("Nonempty account credentials required")
        super().__init__(address, AppHandler)


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, write):
        try:
            authorization = self.headers.get("Authorization", "")
            owner = self.server.tokens.get(authorization[7:]) if authorization.startswith("Bearer ") else None
            if not owner:
                self.send_json(401, {"error": "Unauthorized"})
                return
            url = urlsplit(self.path)
            if not write and url.path == "/collaboration/events":
                after = int(parse_qs(url.query).get("after", ["0"])[0])
                result = self.server.store.events(owner, after)
            elif write and url.path.startswith("/collaboration/sessions/") and url.path.endswith("/outputs"):
                session = url.path.split("/")
                if len(session) != 5:
                    raise ValueError("Invalid route")
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 100000:
                    raise ValueError("Invalid request size")
                result = self.server.store.output(owner, session[3], object_value(json.loads(self.rfile.read(size))))
            else:
                self.send_json(404, {"error": "Not found"})
                return
            self.send_json(200, result)
        except PermissionError:
            self.send_json(403, {"error": "Access denied"})
        except (ValueError, TypeError, KeyError):
            self.send_json(400, {"error": "Invalid request"})

    def send_json(self, status, body):
        data = encoded(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
