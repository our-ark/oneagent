"""Launch OneAgent Travel. Build examples/travel/web before running."""
import argparse
import logging
from pathlib import Path

from .server import Hub, WebServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--root", type=Path, default=Path(".travel-demo"))
    parser.add_argument("--web-root", type=Path, default=Path(__file__).resolve().parents[3] / "examples/travel/web/dist")
    parser.add_argument("--public-origin", help="Exact browser origin, including scheme and port (for an HTTPS reverse proxy)")
    args = parser.parse_args()
    if not (args.web_root / "index.html").is_file():
        parser.error("Build the website first: npm --prefix examples/travel/web ci && npm --prefix examples/travel/web run build")
    logging.basicConfig(level=logging.INFO)
    hub = Hub(args.root)
    server = WebServer((args.host, args.port), hub, args.web_root, args.public_origin)
    print(f"OneAgent Travel: {server.public_origin}", flush=True)
    print("Fictional catalog; real agent responses. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        hub.close()


if __name__ == "__main__":
    main()
