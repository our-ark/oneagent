"""Launch three independent travel websites and an optional Telegram bot."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading

from oneagent.collaboration.store import encoded
from oneagent.config import read_section
from .server import Hub, SITES, WebServer
from .telegram import TelegramDemo


def launch_bot(control_path):
    """Use the normal bot composition, session store, and notification service."""
    env = dict(os.environ, ONEAGENT_TRAVEL_CONTROL_FILE=str(control_path.resolve()))
    return subprocess.Popen(
        [sys.executable, "-c", "from oneagent.app.core import main; main('telegram')"],
        env=env, start_new_session=True,
    )


class ControlServer(ThreadingHTTPServer):
    """Loopback-only, bearer-authenticated bridge for the existing bot daemon."""
    daemon_threads = True

    def __init__(self, controller):
        self.controller = controller
        self.token = secrets.token_hex(32)
        super().__init__(("127.0.0.1", 0), ControlHandler)


class ControlHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        status, result = 200, {}
        try:
            if self.path not in {"/telegram", "/attach"} or not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.server.token):
                raise PermissionError()
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32000:
                raise ValueError()
            body = json.loads(self.rfile.read(size))
            if self.path == "/attach":
                self.server.controller.hub.bind_bot(body["chat_id"], body["url"], body["token"])
                result = {"attached": True}
            else:
                reply = self.server.controller.handle(body["chat_id"], body["user_id"], body["message_id"], body["text"])
                result = {"reply": reply}
        except PermissionError:
            status, result = 403, {"error": "Unauthorized"}
        except (ValueError, KeyError, TypeError):
            status, result = 400, {"error": "Invalid request"}
        except Exception:
            status, result = 503, {"error": "Travel agent unavailable"}
        data = encoded(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080, help="First port; hotels and activities use the next two ports")
    parser.add_argument("--root", type=Path, default=Path(".travel-demo"))
    parser.add_argument("--web-root", type=Path, default=Path(__file__).resolve().parents[3] / "examples/travel/web/dist")
    parser.add_argument("--flights-origin", "--public-origin", dest="flights_origin", help="Exact external origin for the flight site")
    parser.add_argument("--hotels-origin", help="Exact external origin for the hotel site")
    parser.add_argument("--activities-origin", help="Exact external origin for the activities site")
    parser.add_argument("--telegram", action="store_true", help="Also start the normal OneAgent Telegram bot; omit if its daemon is already running")
    args = parser.parse_args()
    if not 1 <= args.port <= 65533:
        parser.error("--port must be between 1 and 65533")
    for app in SITES:
        if not (args.web_root / app / "index.html").is_file():
            parser.error("Build all three websites first: npm --prefix examples/travel/web ci && npm --prefix examples/travel/web run build")
    token, allowed = None, None
    if args.telegram:
        config = read_section("telegram", Path.cwd())
        token = os.environ.get("ONEAGENT_TELEGRAM_BOT_TOKEN") or config.get("bot_token")
        allowed = os.environ.get("ONEAGENT_TELEGRAM_ALLOWED_CHAT_ID") or config.get("allowed_chat_id")
        if not token or not allowed or not str(allowed).isdigit() or int(allowed) <= 0:
            parser.error("Set ONEAGENT_TELEGRAM_BOT_TOKEN and a positive ONEAGENT_TELEGRAM_ALLOWED_CHAT_ID (your private chat ID), or the corresponding telegram config fields.")
    logging.basicConfig(level=logging.INFO)
    hub = Hub(args.root)
    servers, bot = [], None
    try:
        for index, app in enumerate(SITES):
            server = WebServer((args.host, args.port + index), hub, args.web_root,
                               getattr(args, app + "_origin"), app_id=app)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            print(f"{app.title()}: {server.public_origin}", flush=True)
        controller = TelegramDemo(hub)
        control = ControlServer(controller)
        servers.append(control)
        threading.Thread(target=control.serve_forever, daemon=True).start()
        control_path = args.root.resolve() / "control.json"
        control_path.touch(mode=0o600, exist_ok=True)
        control_path.chmod(0o600)
        control_path.write_text(encoded({"url": f"http://127.0.0.1:{control.server_port}/telegram", "token": control.token, "root": str(args.root.resolve())}))
        if args.telegram:
            bot = launch_bot(control_path)
            print("Starting the normal Telegram bot. Once it is listening, send /traveldemo in your private chat.", flush=True)
        else:
            print(f"Existing bot: set ONEAGENT_TRAVEL_CONTROL_FILE={control_path} before starting its daemon.", flush=True)
        print("Fictional catalog; real agent responses. Ctrl+C to stop.", flush=True)
        if bot:
            code = bot.wait()
            if code:
                raise SystemExit(code)
        else:
            threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if bot and bot.poll() is None:
            bot.terminate()
            try:
                bot.wait(timeout=15)
            except subprocess.TimeoutExpired:
                bot.kill()
                bot.wait()
        for server in servers:
            server.shutdown()
            server.server_close()
        hub.close()


if __name__ == "__main__":
    main()
