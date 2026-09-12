"""Fictional travel facts and app-owned, idempotent saved-trip operations."""
from __future__ import annotations

from datetime import datetime, timedelta
from importlib.resources import files
import json
from pathlib import Path
import sqlite3

from oneagent.collaboration import MessageStore, Tool, ToolRegistry
from oneagent.collaboration.store import encoded, object_value

CATALOG = json.loads(files("oneagent.travel").joinpath("data/catalog.json").read_text())


def item(kind, item_id):
    for entry in CATALOG[kind]:
        if entry["id"] == item_id:
            return object_value(entry)
    raise ValueError("Unknown catalog item")


class TripStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        db = self.connect()
        try:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS trips(owner TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(owner TEXT, id TEXT, request TEXT, result TEXT, PRIMARY KEY(owner,id));
            """)
            db.commit()
        finally:
            db.close()

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def has_receipt(self, owner, request_id):
        db = self.connect()
        try:
            return bool(db.execute("SELECT 1 FROM receipts WHERE owner=? AND id=?", (owner, request_id)).fetchone())
        finally:
            db.close()

    def get(self, owner):
        db = self.connect()
        try:
            row = db.execute("SELECT body FROM trips WHERE owner=?", (owner,)).fetchone()
        finally:
            db.close()
        state = json.loads(row[0]) if row else {"budget_cents": 150000, "preferences": "", "flight_id": None, "hotel_id": None, "activity_id": None}
        return self.enrich(state)

    def update(self, owner, changes, request_id):
        allowed = {"budget_cents", "preferences", "flight_id", "hotel_id", "activity_id"}
        if not changes or not set(changes).issubset(allowed):
            raise ValueError("Invalid trip update")
        if "budget_cents" in changes and (type(changes["budget_cents"]) is not int or not 10000 <= changes["budget_cents"] <= 5000000):
            raise ValueError("Budget must be between $100 and $50,000")
        if "preferences" in changes and (not isinstance(changes["preferences"], str) or len(changes["preferences"]) > 2000):
            raise ValueError("Preferences must be at most 2,000 characters")
        for key, kind in [("flight_id", "flights"), ("hotel_id", "hotels"), ("activity_id", "activities")]:
            if changes.get(key) is not None:
                item(kind, changes[key])
        db = self.connect()
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                receipt = db.execute("SELECT request,result FROM receipts WHERE owner=? AND id=?", (owner, request_id)).fetchone()
                if receipt:
                    if receipt[0] != encoded(changes):
                        raise ValueError("Conflicting action ID")
                    return json.loads(receipt[1])
                row = db.execute("SELECT body FROM trips WHERE owner=?", (owner,)).fetchone()
                state = json.loads(row[0]) if row else {"budget_cents": 150000, "preferences": "", "flight_id": None, "hotel_id": None, "activity_id": None}
                state.update(changes)
                db.execute("INSERT INTO trips VALUES (?,?) ON CONFLICT(owner) DO UPDATE SET body=excluded.body", (owner, encoded(state)))
                result = self.enrich(state)
                db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (owner, request_id, encoded(changes), encoded(result)))
                return result
        finally:
            db.close()

    @staticmethod
    def enrich(state):
        result = dict(state, destination="Tokyo", check_in=CATALOG["check_in"], check_out=CATALOG["check_out"], nights=3)
        flight = item("flights", state["flight_id"]) if state["flight_id"] else None
        hotel = item("hotels", state["hotel_id"]) if state["hotel_id"] else None
        activity = item("activities", state["activity_id"]) if state.get("activity_id") else None
        result.update(flight=flight, hotel=hotel, activity=activity, activity_id=state.get("activity_id"))
        result["total_cents"] = (flight["price_cents"] if flight else 0) + (hotel["nightly_cents"] * 3 if hotel else 0) + (activity["price_cents"] if activity else 0)
        result["remaining_cents"] = result["budget_cents"] - result["total_cents"]
        warnings = []
        if result["remaining_cents"] < 0:
            warnings.append("Your saved selections exceed your trip budget.")
        if flight and hotel:
            arrival = datetime.fromisoformat(flight["arrival_at"])
            estimated = arrival + timedelta(minutes=60 + hotel["transfer_minutes"][flight["arrival_airport"]])
            result["estimated_hotel_arrival"] = estimated.isoformat()
            closing = datetime.fromisoformat(CATALOG["check_in"] + "T" + hotel["check_in_until"] + ":00+09:00")
            opening = datetime.fromisoformat(CATALOG["check_in"] + "T" + hotel["check_in_from"] + ":00+09:00")
            if not hotel["late_check_in"] and estimated > closing:
                warnings.append("Estimated arrival is after this hotel's reception closes. Choose a hotel with 24-hour reception or an earlier flight.")
            if estimated < opening:
                warnings.append("You may arrive before room check-in. Ask about luggage storage.")
        if activity and flight:
            earliest = datetime.fromisoformat(flight["arrival_at"]) + timedelta(minutes=120)
            if datetime.fromisoformat(activity["starts_at"]) < earliest:
                warnings.append("This activity starts too soon after your flight arrives. Allow time for arrival formalities and travel into the city.")
        result["warnings"] = warnings
        return result


class TravelMessageStore(MessageStore):
    def snapshot_context(self, context):
        context = object_value(context)
        selected = context.get("selected_id")
        result = {"revision": context.get("revision", 0), "app": self.app_id,
                  "dataset": "Fictional demo; USD; Nov 6–9, 2026; three nights; flights are one-way; hotel totals include mock taxes."}
        if selected and self.app_id in {"flights", "hotels", "activities"}:
            result["selected_object"] = item(self.app_id, selected)
        return result


def travel_tools(trips):
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
    registry.register(Tool("trip.get", "Read the user's saved trip, budget and preferences", {"type": "object", "properties": {}, "additionalProperties": False}, lambda owner, args, key: trips.get(owner), no_args))
    def brief(args):
        if not args or not set(args).issubset({"budget_cents", "preferences"}):
            raise ValueError("Specify budget_cents or preferences")
        if "budget_cents" in args and (type(args["budget_cents"]) is not int or not 10000 <= args["budget_cents"] <= 5000000):
            raise ValueError("Invalid budget")
        if "preferences" in args and (not isinstance(args["preferences"], str) or len(args["preferences"]) > 2000):
            raise ValueError("Invalid preferences")
    registry.register(Tool("trip.update_brief", "Update the user's stated budget or preferences after confirmation",
        {"type": "object", "properties": {"budget_cents": {"type": "integer"}, "preferences": {"type": "string"}}, "additionalProperties": False},
        lambda owner, args, key: trips.update(owner, args, key), brief, True))
    for kind, field in [("flight", "flight_id"), ("hotel", "hotel_id"), ("activity", "activity_id")]:
        registry.register(Tool(f"trip.save_{kind}", f"Save the selected {kind} to the trip; this is not a booking", {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"], "additionalProperties": False},
            lambda owner, args, key, field=field: trips.update(owner, {field: args["id"]}, key), selected, True))
    return registry
