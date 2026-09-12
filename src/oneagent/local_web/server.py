from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import socket
import threading
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from oneagent.local_web.conversation import json_bytes, query_token, recent_conversation_turns
from oneagent.local_web.page import SHOP_PAGE_HTML
from oneagent.local_web.product_page import gallery_asset
from oneagent.local_web.settings import LocalWebSettings, load_local_web_settings
from oneagent.local_web.shortlist import (
    SHORTLIST_ID_RE,
    ShopShortlist,
    backfill_shortlists_from_history,
    latest_shortlist,
    load_shortlist,
)
from oneagent.local_web.thumbs import cached_thumbnail
from oneagent.providers.contracts import ConversationId


_SHOP_PATH = re.compile(r"^/shop(?:/(?P<sid>t[1-9]\d*)(?:/(?P<tab>[1-9]\d*))?)?/?$")
_API_SHOP = re.compile(
    r"^/api/shop(?:/(?P<sid>t[1-9]\d*)(?:/thumb/(?P<thumb>[1-9]\d*))?)?/?$"
)
_API_CHAT_RESULT = re.compile(r"^/api/chat/(?P<request_id>[0-9a-f]{32})$")


class _ChatRequests:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, dict[str, str]] = {}

    def create(self) -> str | None:
        with self._lock:
            for key in list(self._requests):
                if len(self._requests) < 64:
                    break
                if self._requests[key]["status"] != "pending":
                    del self._requests[key]
            if len(self._requests) >= 64:
                return None
            key = uuid4().hex
            self._requests[key] = {"request_id": key, "status": "pending", "reply": ""}
            return key

    def get(self, key: str) -> dict[str, str] | None:
        with self._lock:
            value = self._requests.get(key)
            return dict(value) if value else None

    def finish(self, key: str, reply: str, *, failed: bool = False) -> None:
        with self._lock:
            self._requests[key].update(status="failed" if failed else "completed", reply=reply)


@dataclass
class LocalWebHost:
    root: Path
    conversation_id: ConversationId | Callable[[], ConversationId | None] | None
    handle_chat: Callable[[str, str, int | None], str]

    def resolve_conversation_id(self) -> ConversationId | None:
        value = self.conversation_id
        if callable(value):
            return value()
        return value


class LocalWebServer:
    def __init__(self, httpd: ThreadingHTTPServer, settings: LocalWebSettings) -> None:
        self._httpd = httpd
        self.settings = settings
        self._thread = threading.Thread(
            target=httpd.serve_forever,
            name="oneagent-local-web",
            daemon=True,
        )

    @property
    def port(self) -> int:
        return int(self._httpd.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout_seconds: float = 2.0) -> None:
        self._httpd.shutdown()
        self._thread.join(timeout=max(0.0, timeout_seconds))
        self._httpd.server_close()


def start_local_web(
    host: LocalWebHost,
    *,
    settings: LocalWebSettings | None = None,
) -> LocalWebServer | None:
    resolved = settings or load_local_web_settings(host.root)
    if not resolved.enabled:
        return None
    try:
        backfill_shortlists_from_history(host.root)
    except (OSError, ValueError):
        pass
    server_class = ThreadingHTTPServer
    if resolved.host == "::1":
        class IPv6Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6
        server_class = IPv6Server
    httpd = server_class(
        (resolved.host, resolved.port),
        _handler_class(host, resolved),
    )
    resolved.port = int(httpd.server_address[1])
    server = LocalWebServer(httpd, resolved)
    server.start()
    return server


def _handler_class(host: LocalWebHost, settings: LocalWebSettings):
    requests = _ChatRequests()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if not self._authorized(parsed.path):
                self._send(401, {"error": "token required"})
                return
            shop = _SHOP_PATH.fullmatch(parsed.path)
            if parsed.path.startswith("/assets/syryn/"):
                asset = gallery_asset(parsed.path.removeprefix("/assets/syryn/"))
                if asset is None:
                    self._send(404, {"error": "not found"})
                else:
                    self._send_bytes(200, asset, "image/jpeg")
                return
            if shop:
                self._send_html(SHOP_PAGE_HTML)
                return
            api = _API_SHOP.fullmatch(parsed.path)
            if api:
                shortlist_id = api.group("sid")
                thumb = api.group("thumb")
                if thumb:
                    image = cached_thumbnail(
                        shortlist_id or "",
                        int(thumb),
                        root=host.root,
                    )
                    if image is None:
                        self._send(404, {"error": "No thumbnail yet."})
                        return
                    body, content_type = image
                    self._send_bytes(200, body, content_type)
                    return
                shortlist = _resolve_shortlist(host.root, shortlist_id)
                if shortlist is None:
                    self._send(404, {"error": "No shop shortlist yet."})
                    return
                self._send(200, shortlist.to_json())
                return
            if parsed.path.rstrip("/") == "/api/conversation":
                self._send(
                    200,
                    {
                        "turns": recent_conversation_turns(
                            root=host.root,
                            chat_id=host.resolve_conversation_id(),
                        )
                    },
                )
                return
            chat_result = _API_CHAT_RESULT.fullmatch(parsed.path)
            if chat_result:
                result = requests.get(chat_result.group("request_id"))
                self._send(200 if result else 404, result or {"error": "request not found"})
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if not self._authorized(parsed.path):
                self._send(401, {"error": "token required"})
                return
            if parsed.path.rstrip("/") != "/api/chat":
                self._send(404, {"error": "not found"})
                return
            if host.resolve_conversation_id() is None:
                self._send(409, {"error": "Configure an allowed chat before using browser chat."})
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._send(400, {"error": "invalid body"})
                return
            if length < 1 or length > 8000:
                self._send(400, {"error": "invalid body"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                self._send(400, {"error": "invalid json"})
                return
            if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
                self._send(400, {"error": "JSON object with text required"})
                return
            text = payload["text"].strip()
            if not text:
                self._send(400, {"error": "text required"})
                return
            shortlist_id = str((payload or {}).get("shortlist_id") or "").strip()
            tab = _optional_tab((payload or {}).get("tab"))
            request_id = requests.create()
            if request_id is None:
                self._send(429, {"error": "Too many pending messages. Try again shortly."})
                return
            worker = threading.Thread(
                target=_run_local_web_chat,
                args=(host, text, shortlist_id, tab, requests, request_id),
                name="oneagent-local-web-chat",
                daemon=True,
            )
            worker.start()
            self._send(202, {"status": "accepted", "reply": "", "request_id": request_id})

        def _authorized(self, path: str) -> bool:
            header = self.headers.get("Authorization") or ""
            bearer = header[7:].strip() if header.lower().startswith("bearer ") else ""
            token = bearer or query_token(self.path)
            return bool(settings.token) and secrets.compare_digest(token.encode(), settings.token.encode())

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, max-age=86400")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _run_local_web_chat(
    host: LocalWebHost,
    text: str,
    shortlist_id: str,
    tab: int | None,
    requests: _ChatRequests,
    request_id: str,
) -> None:
    try:
        reply = host.handle_chat(text, shortlist_id, tab)
    except Exception as error:
        requests.finish(request_id, f"Could not process this message ({type(error).__name__}).", failed=True)
    else:
        requests.finish(request_id, reply)


def _optional_tab(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        tab = int(value)
    except (TypeError, ValueError):
        return None
    return tab if tab > 0 else None


def _resolve_shortlist(root: Path, shortlist_id: str | None) -> ShopShortlist | None:
    if shortlist_id:
        if not SHORTLIST_ID_RE.fullmatch(shortlist_id):
            return None
        return load_shortlist(shortlist_id, root=root)
    return latest_shortlist(root=root)
