"""Read-only fictional catalogs and the context currently viewed on a website."""
from __future__ import annotations

from importlib.resources import files
import json

from oneagent.collaboration import MessageStore, Tool, ToolRegistry
from oneagent.collaboration.store import object_value

CATALOG = json.loads(files("oneagent.travel").joinpath("data/catalog.json").read_text())


def item(kind, item_id):
    for entry in CATALOG[kind]:
        if entry["id"] == item_id:
            return object_value(entry)
    raise ValueError("Unknown catalog item")


class TravelMessageStore(MessageStore):
    def snapshot_context(self, context):
        context = object_value(context)
        selected = context.get("selected_id")
        result = {"revision": context.get("revision", 0), "app": self.app_id,
                  "dataset": "Fictional demo; USD; Nov 6–9, 2026; three nights; flights are one-way; hotel totals include mock taxes."}
        if selected and self.app_id in {"flights", "hotels", "activities"}:
            result["selected_object"] = item(self.app_id, selected)
        return result


def travel_tools():
    registry = ToolRegistry()
    def no_args(args):
        if args:
            raise ValueError("This tool takes no arguments")
    def selected(args):
        if set(args) != {"id"} or not isinstance(args["id"], str):
            raise ValueError("An item ID is required")
    for kind in ["flights", "hotels", "activities"]:
        registry.register(Tool(f"{kind}.search", f"Read the fictional {kind} catalog", {"type": "object", "properties": {}, "additionalProperties": False},
            lambda owner, args, key, kind=kind: CATALOG[kind], no_args))
        registry.register(Tool(f"{kind}.get", f"Read authoritative {kind} details by ID", {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"], "additionalProperties": False},
            lambda owner, args, key, kind=kind: item(kind, args["id"]), selected))
    return registry
