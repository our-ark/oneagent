"""Local product page snapshots, matched only to their original merchant URL."""

from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import urlparse


ASSET_ROOT = Path(__file__).with_name("assets") / "syryn"


@lru_cache(maxsize=1)
def _syryn_snapshot() -> dict:
    return json.loads((ASSET_ROOT / "product.json").read_text(encoding="utf-8"))


def product_page_snapshot(url: str) -> dict | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"underwateraudio.com", "www.underwateraudio.com"}
        and parsed.path.rstrip("/") == "/products/syryn-mp3-player"
    ):
        return _syryn_snapshot()
    return None


def gallery_asset(name: str) -> bytes | None:
    if name not in {f"{i}.jpg" for i in range(1, 8)}:
        return None
    return (ASSET_ROOT / name).read_bytes()
