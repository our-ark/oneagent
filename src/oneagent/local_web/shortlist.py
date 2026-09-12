from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from oneagent.paths import artifact_path
from oneagent.local_web.product_page import product_page_snapshot
from oneagent.state import atomic_write, load_json_object
from oneagent.tasks.queue import TaskJob, task_queue_status


MARKDOWN_LINK_RE = re.compile(
    r"\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)"
)
URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
SHORTLIST_ID_RE = re.compile(r"^t[1-9]\d*$")
CARD_HEADER_RE = re.compile(r"^(?P<num>\d+)[.)]\s+(?P<body>.+)$")
CARD_NAME_PRICE_RE = re.compile(
    r"^(?P<name>.+?)\s+[—–-]\s+(?P<price>\$\s*[\d.,]+(?:\s+[A-Z]{3})?)\s*$"
)
CARD_FIELD_RE = re.compile(
    r"^(?P<key>[A-Za-z][A-Za-z0-9/ _-]{0,40}):\s*(?P<value>.+)$"
)
PLACEHOLDER_NAME_RE = re.compile(r"^option\s+\d+$", re.I)
REFERENCED_SHORTLIST_RE = re.compile(r"\bshortlist\s+(t[1-9]\d*)\b", re.I)
PRODUCT_PATH_RE = re.compile(r"/(?:products?|ip|dp|gp/product)/[^/]+", re.I)
MAX_LABEL_CHARS = 80
MAX_SHORTLIST_PRODUCTS = 4


@dataclass(frozen=True)
class ShopProduct:
    index: int
    name: str
    url: str
    store: str = ""
    price: str = ""
    variant: str = ""
    detail: str = ""


@dataclass(frozen=True)
class ShopShortlist:
    id: str
    task_id: int
    title: str
    products: tuple[ShopProduct, ...]
    notes: str = ""
    conversation_id: int | None = None

    def to_json(self) -> dict[str, object]:
        payload = asdict(self)
        payload["products"] = [
            {**asdict(product), "brand": product_brand(product),
             "page": product_page_snapshot(product.url)}
            for product in self.products
        ]
        return payload


def product_brand(product: ShopProduct) -> str:
    store = _clean_label(product.store)
    if store:
        cleaned = re.sub(r"\s+online store$", "", store, flags=re.I)
        cleaned = re.sub(r"\s+(?:store|shop)$", "", cleaned, flags=re.I).strip()
        return cleaned or store
    name = _clean_label(product.name)
    if name:
        return name.split()[0]
    host = _merchant_label_from_url(product.url)
    return host or f"Option {product.index}"


def extract_products(text: str) -> tuple[ShopProduct, ...]:
    table_products = _products_from_markdown_table(text)
    if table_products:
        return table_products
    card_products = _products_from_cards(text)
    if card_products:
        return card_products
    return _products_from_product_urls(text)


def record_shortlist_from_task(
    job: TaskJob,
    result: str,
    *,
    root: Path | None = None,
    conversation_id: int | None = None,
) -> ShopShortlist | None:
    if job.status != "completed":
        return None
    referenced = _referenced_shortlist_id(job.text)
    if referenced and load_shortlist(referenced, root=root) is not None:
        return None
    products = extract_products(result or job.result)
    if not _usable_catalog_products(products):
        return None
    shortlist = ShopShortlist(
        id=f"t{job.id}",
        task_id=job.id,
        title=_title_from_request(job.text),
        products=products,
        notes=_notes_after_products(result or job.result),
        conversation_id=conversation_id if conversation_id is not None else job.chat_id,
    )
    save_shortlist(shortlist, root=root)
    return shortlist


def backfill_shortlists_from_history(root: Path | None = None) -> tuple[ShopShortlist, ...]:
    recorded: list[ShopShortlist] = []
    for job in task_queue_status(root).history:
        existing = load_shortlist(f"t{job.id}", root=root)
        if job.status != "completed":
            if existing is not None:
                _forget_shortlist(existing.id, root)
            continue
        if existing is not None and _usable_catalog_products(existing.products):
            continue
        shortlist = record_shortlist_from_task(job, job.result, root=root)
        if shortlist is not None:
            recorded.append(shortlist)
            continue
        if existing is not None:
            _forget_shortlist(existing.id, root)
    return tuple(recorded)


def save_shortlist(shortlist: ShopShortlist, *, root: Path | None = None) -> Path:
    path = shortlist_path(shortlist.id, root)
    atomic_write(path, json.dumps(shortlist.to_json(), indent=2) + "\n")
    _update_index(shortlist.id, root)
    return path


def load_shortlist(shortlist_id: str, *, root: Path | None = None) -> ShopShortlist | None:
    cleaned = shortlist_id.strip()
    if not SHORTLIST_ID_RE.fullmatch(cleaned):
        return None
    path = shortlist_path(cleaned, root)
    if not path.exists():
        return None
    data = load_json_object(path)
    products = tuple(
        ShopProduct(
            index=int(item.get("index") or index),
            name=str(item.get("name") or f"Option {index}"),
            url=str(item.get("url") or ""),
            store=str(item.get("store") or ""),
            price=str(item.get("price") or ""),
            variant=str(item.get("variant") or ""),
            detail=str(item.get("detail") or ""),
        )
        for index, item in enumerate(data.get("products") or [], start=1)
        if isinstance(item, dict) and str(item.get("url") or "").startswith("http")
    )
    if not products:
        return None
    return ShopShortlist(
        id=cleaned,
        task_id=int(data.get("task_id") or 0),
        title=str(data.get("title") or cleaned),
        products=products,
        notes=str(data.get("notes") or ""),
        conversation_id=_optional_int(data.get("conversation_id")),
    )


def format_shortlist_followup(
    user_text: str,
    shortlist: ShopShortlist,
    *,
    tab: int | None = None,
) -> str:
    lines = [
        "Current shop shortlist from OneAgent's last product search. "
        "Use this list whenever the human says these, them, the kettles, "
        "option 2, this one, or similar. Do not ask for names or URLs that "
        "are already listed. If they ask about reviews, look the products up; "
        "do not invent ratings.",
        f"Shortlist: {shortlist.id}",
        f"Need: {shortlist.title}",
        "Products:",
    ]
    for product in shortlist.products:
        viewing = " [currently viewing this tab]" if tab == product.index else ""
        extras = [
            part
            for part in (product.price, product.store, product.variant)
            if part
        ]
        headline = f"{product.index}.{viewing} {product.name}"
        if extras:
            headline += " — " + " — ".join(extras)
        lines.append(headline)
        lines.append(f"   {product.url}")
        if product.detail:
            lines.append(f"   {product.detail}")
        snapshot = product_page_snapshot(product.url)
        if snapshot and tab == product.index:
            lines.append(f"   Merchant page snapshot checked {snapshot['checked_at']} (verify current price and stock before advising a purchase):")
            for variant in snapshot["variants"]:
                lines.append(
                    f"   {variant['name']}: {variant['price']:.2f} {snapshot['currency']}; "
                    f"{'available' if variant['available'] else 'unavailable'} in snapshot."
                )
    if shortlist.notes:
        lines.append("Notes:")
        lines.append(shortlist.notes[:1200])
    lines.append("Human question:")
    lines.append(user_text.strip())
    return "\n".join(lines)


def resolve_followup_shortlist(
    shortlist_id: str = "",
    *,
    root: Path | None = None,
) -> ShopShortlist | None:
    cleaned = shortlist_id.strip()
    if cleaned:
        found = load_shortlist(cleaned, root=root)
        if found is not None:
            return found
    return latest_shortlist(root=root)


def latest_shortlist(*, root: Path | None = None) -> ShopShortlist | None:
    data = load_json_object(_index_path(root)) if _index_path(root).exists() else {}
    latest = str(data.get("latest") or "").strip()
    if latest:
        found = load_shortlist(latest, root=root)
        if found is not None:
            return found
    ids = [str(item) for item in data.get("ids") or [] if str(item).strip()]
    for stored_id in reversed(ids):
        found = load_shortlist(stored_id, root=root)
        if found is not None:
            return found
    return None


def shortlist_path(shortlist_id: str, root: Path | None = None) -> Path:
    return artifact_path(Path("shop") / "shortlists" / f"{shortlist_id}.json", root)


def _index_path(root: Path | None) -> Path:
    return artifact_path(Path("shop") / "shortlists" / "index.json", root)


def _update_index(shortlist_id: str, root: Path | None) -> None:
    path = _index_path(root)
    data = load_json_object(path) if path.exists() else {}
    ids = [str(item) for item in data.get("ids") or [] if str(item).strip()]
    if shortlist_id not in ids:
        ids.append(shortlist_id)
    atomic_write(
        path,
        json.dumps({"latest": shortlist_id, "ids": ids}, indent=2) + "\n",
    )


def _products_from_markdown_table(text: str) -> tuple[ShopProduct, ...]:
    lines = text.splitlines()
    tables = _markdown_tables(lines)
    if len(tables) != 1:
        return ()
    start, end = tables[0]
    rows = [_split_table_cells(line) for line in lines[start:end]]
    if len(rows) < 3 or not _is_separator_row(rows[1]):
        return ()
    headers = [cell.strip().lower() for cell in rows[0]]
    products: list[ShopProduct] = []
    for cells in rows[2:]:
        product = _product_from_cells(len(products) + 1, headers, cells)
        if product is not None:
            products.append(product)
    return tuple(products)


def _products_from_cards(text: str) -> tuple[ShopProduct, ...]:
    products: list[ShopProduct] = []
    seen: set[str] = set()
    for block in _card_blocks(text):
        product = _product_from_card(len(products) + 1, block)
        if product is None or product.url in seen:
            continue
        seen.add(product.url)
        products.append(product)
    return tuple(products)


def _card_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if CARD_HEADER_RE.match(line.strip())
    ]
    blocks: list[str] = []
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else len(lines)
        chunk: list[str] = []
        for line in lines[start:end]:
            if "telegram:break" in line:
                break
            chunk.append(line)
        block = "\n".join(chunk)
        if _product_url_in(block):
            blocks.append(block)
    return blocks


def _product_from_card(index: int, block: str) -> ShopProduct | None:
    url, link_name, leftover = _best_product_link(block)
    if not url:
        return None
    header = ""
    match = CARD_HEADER_RE.match(block.splitlines()[0].strip())
    if match is not None:
        header = match.group("body").strip()
    name = _clean_label(
        link_name or _name_from_card_header(header) or leftover
    )
    store = _clean_label(
        leftover if leftover and link_name else _card_field(block, "store", "merchant", "seller")
    )
    price = _price_from_card_header(header) or _card_field(block, "price")
    if not name or (not store and not price):
        return None
    return ShopProduct(
        index=index,
        name=name,
        url=url,
        store=store,
        price=price,
        variant=_card_field(block, "variant"),
        detail=_card_detail(block),
    )


def _name_from_card_header(body: str) -> str:
    cleaned = MARKDOWN_LINK_RE.sub(lambda match: match.group("label"), body).strip()
    priced = CARD_NAME_PRICE_RE.match(cleaned)
    if priced is not None:
        return priced.group("name").strip(" \t-*")
    return cleaned.strip(" \t-*")


def _price_from_card_header(body: str) -> str:
    priced = CARD_NAME_PRICE_RE.match(
        MARKDOWN_LINK_RE.sub(lambda match: match.group("label"), body).strip()
    )
    return priced.group("price").strip() if priced is not None else ""


def _card_field(block: str, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for line in block.splitlines():
        match = CARD_FIELD_RE.match(line.strip())
        if match is not None and match.group("key").strip().lower() in wanted:
            return match.group("value").strip()
    return ""


def _card_detail(block: str) -> str:
    skip = {"store", "merchant", "seller", "variant", "need", "price"}
    parts: list[str] = []
    for line in block.splitlines():
        match = CARD_FIELD_RE.match(line.strip())
        if match is None:
            continue
        key = match.group("key").strip().lower()
        value = match.group("value").strip()
        if key in skip or key in {"http", "https"} or not value:
            continue
        parts.append(f"{key}: {value}")
    return " · ".join(parts)


def _products_from_product_urls(text: str) -> tuple[ShopProduct, ...]:
    products: list[ShopProduct] = []
    seen: set[str] = set()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        url, name, leftover = _primary_link(line)
        if not _is_product_url(url) or url in seen:
            continue
        if leftover.lstrip().startswith("#"):
            continue
        context = _nearby_card_context(lines, index)
        product_name = _clean_label(name or leftover or context["name"])
        store = _clean_label((leftover if name else "") or context["store"])
        if not product_name or (not store and not context["price"]):
            continue
        seen.add(url)
        products.append(
            ShopProduct(
                index=len(products) + 1,
                name=product_name,
                url=url,
                store=store,
                price=context["price"],
                variant=context["variant"],
                detail=context["detail"],
            )
        )
        if len(products) >= MAX_SHORTLIST_PRODUCTS:
            break
    return tuple(products)


def _nearby_card_context(lines: list[str], url_index: int) -> dict[str, str]:
    start = url_index
    while start > 0:
        previous = lines[start - 1].strip()
        if not previous or "telegram:break" in previous:
            break
        start -= 1
        if CARD_HEADER_RE.match(previous):
            break
    block = "\n".join(lines[start : url_index + 1])
    header = ""
    match = CARD_HEADER_RE.match(lines[start].strip()) if start <= url_index else None
    if match is not None:
        header = match.group("body").strip()
    return {
        "name": _name_from_card_header(header) if header else "",
        "store": _card_field(block, "store", "merchant", "seller"),
        "price": _price_from_card_header(header) if header else "",
        "variant": _card_field(block, "variant"),
        "detail": _card_detail(block),
    }


def _product_from_cells(
    index: int,
    headers: list[str],
    cells: list[str],
) -> ShopProduct | None:
    url = ""
    name = ""
    leftover = ""
    for cell in cells:
        found_url, found_name, found_leftover = _primary_link(cell)
        if found_url:
            url = found_url
            name = found_name
            leftover = found_leftover
            break
    if not url:
        return None
    fields = {
        header: MARKDOWN_LINK_RE.sub(lambda match: match.group("label"), cell).strip()
        for header, cell in zip(headers, cells)
        if header
    }
    product_name = _clean_label(name) or f"Option {index}"
    store = _clean_label(leftover or fields.get("store", ""))
    return ShopProduct(
        index=index,
        name=product_name,
        url=url,
        store=store,
        price=_first_field(fields, "price") or next(
            (value for header, value in fields.items() if header.startswith("price ")),
            "",
        ),
        variant=_first_field(fields, "exact variant", "variant"),
        detail=_product_detail(fields),
    )


def _product_detail(fields: dict[str, str]) -> str:
    skip = {"product / merchant", "product", "merchant", "price", "exact variant", "variant"}
    parts = [
        f"{header}: {value}"
        for header, value in fields.items()
        if header not in skip and value
    ]
    return " · ".join(parts)


def _first_field(fields: dict[str, str], *names: str) -> str:
    for name in names:
        if fields.get(name):
            return fields[name]
    return ""


def _markdown_tables(lines: list[str]) -> list[tuple[int, int]]:
    tables: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if _is_table_line(lines[index]):
            start = index
            index += 1
            while index < len(lines) and _is_table_line(lines[index]):
                index += 1
            if index - start >= 3:
                tables.append((start, index))
            continue
        index += 1
    return tables


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.count("|") >= 2


def _split_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(
        TABLE_SEPARATOR_CELL_RE.fullmatch(cell or "") for cell in cells
    )


def _primary_link(cell: str) -> tuple[str, str, str]:
    match = MARKDOWN_LINK_RE.search(cell)
    if match is not None:
        leftover = f"{cell[: match.start()]}{cell[match.end() :]}".strip(" \t|-–—*")
        return match.group("url"), match.group("label").strip(), leftover
    url_match = URL_RE.search(cell)
    if url_match is not None:
        leftover = f"{cell[: url_match.start()]}{cell[url_match.end() :]}".strip()
        return url_match.group(0), leftover, ""
    return "", "", ""


def _title_from_request(text: str) -> str:
    cleaned = " ".join(text.split())
    for prefix in ("Use the shop skill.", "Do not create a cart or check out."):
        cleaned = cleaned.replace(prefix, "")
    return cleaned.strip()[:160] or "Shop shortlist"


def _notes_after_products(text: str) -> str:
    lines = text.splitlines()
    tables = _markdown_tables(lines)
    if len(tables) == 1:
        footer = "\n".join(lines[tables[0][1] :]).strip()
        return footer[:1500]
    last = 0
    for index, line in enumerate(lines):
        if _product_url_in(line):
            last = index + 1
    footer = "\n".join(lines[last:]).strip()
    return footer[:1500]


def _has_placeholder_products(shortlist: ShopShortlist) -> bool:
    return not _usable_catalog_products(shortlist.products)


def _usable_catalog_products(products: tuple[ShopProduct, ...]) -> bool:
    if not 1 <= len(products) <= MAX_SHORTLIST_PRODUCTS:
        return False
    return all(_is_catalog_product(product) for product in products)


def _is_catalog_product(product: ShopProduct) -> bool:
    if not _is_product_url(product.url):
        return False
    if not _clean_label(product.name):
        return False
    if product.store and not _clean_label(product.store):
        return False
    return True


def _clean_label(value: str) -> str:
    text = " ".join(value.split())
    if not text or len(text) > MAX_LABEL_CHARS:
        return ""
    if text.startswith("#") or text.startswith("<!--"):
        return ""
    if PLACEHOLDER_NAME_RE.fullmatch(text):
        return ""
    return text


def _referenced_shortlist_id(text: str) -> str:
    match = REFERENCED_SHORTLIST_RE.search(text)
    return match.group(1).lower() if match is not None else ""


def _forget_shortlist(shortlist_id: str, root: Path | None) -> None:
    path = shortlist_path(shortlist_id, root)
    if path.exists():
        path.unlink()
    index = _index_path(root)
    if not index.exists():
        return
    data = load_json_object(index)
    ids = [
        str(item).strip()
        for item in data.get("ids") or []
        if str(item).strip() and str(item).strip() != shortlist_id
    ]
    latest = str(data.get("latest") or "").strip()
    if latest == shortlist_id:
        latest = ids[-1] if ids else ""
    atomic_write(
        index,
        json.dumps({"latest": latest, "ids": ids}, indent=2) + "\n",
    )


def _is_product_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and bool(PRODUCT_PATH_RE.search(parsed.path))
        )
    except ValueError:
        return False


def _product_url_in(text: str) -> bool:
    return any(_is_product_url(url) for url in URL_RE.findall(text))


def _best_product_link(text: str) -> tuple[str, str, str]:
    for line in text.splitlines():
        url, name, leftover = _primary_link(line)
        if _is_product_url(url):
            return url, name, leftover
    return "", "", ""


def _merchant_label_from_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for prefix in ("www.", "checkout.", "shop.", "store.", "buy."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    labels = [part for part in host.split(".") if part and part not in {"com", "co", "io", "net", "org", "shop"}]
    if not labels:
        return ""
    return labels[0].replace("-", " ").title()


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
