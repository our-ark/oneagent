"""Application-owned, account-scoped message/context storage. No domain assumptions."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identifier(value):
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ValueError("Expected a nonempty identifier of at most 200 characters")
    return value


def object_value(value):
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return json.loads(encoded(value))


class MessageStore:
    """Use authenticated owner IDs; never accept an owner supplied by a browser.

    Override snapshot_context to validate/enrich app facts. shared_fields lists
    fields this app supports; each message must separately authorize disclosure.
    """
    def __init__(self, path: Path, app_id: str, *, shared_fields=()):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.app_id = identifier(app_id)
        self.shared_fields = frozenset(shared_fields)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, owner TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    cursor INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL,
                    id TEXT NOT NULL, session TEXT NOT NULL, body TEXT NOT NULL,
                    UNIQUE(owner,id));
                CREATE TABLE IF NOT EXISTS outputs(
                    owner TEXT NOT NULL, id TEXT NOT NULL, session TEXT NOT NULL,
                    reply_to TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(owner,id), UNIQUE(owner,reply_to));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def session(self, owner: str):
        owner = identifier(owner)
        session_id = uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?,?)", (session_id, owner))
        return {"app_id": self.app_id, "session_id": session_id}

    def _session(self, db, owner, session_id):
        if not db.execute("SELECT 1 FROM sessions WHERE id=? AND owner=?", (session_id, owner)).fetchone():
            raise PermissionError("Unknown session")

    def snapshot_context(self, context):
        return object_value(context)

    def message(self, owner: str, body: dict):
        message_id, session = identifier(body.get("id")), identifier(body.get("session_id"))
        text = body.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 16000:
            raise ValueError("Message text must contain 1-16000 characters")
        shared = body.get("share", [])
        if not isinstance(shared, list) or any(not isinstance(k, str) or k not in self.shared_fields for k in shared):
            raise ValueError("Unsupported disclosure fields")
        event = {"app_id": self.app_id, "event_id": message_id, "session_id": session,
                 "message": {"id": message_id, "text": text},
                 "context": self.snapshot_context(body.get("context", {})), "share": sorted(set(shared))}
        serialized = encoded(event)
        if len(serialized.encode()) > 100000:
            raise ValueError("Context exceeds 100 KB")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._session(db, owner, session)
            old = db.execute("SELECT * FROM events WHERE owner=? AND id=?", (owner, message_id)).fetchone()
            if old:
                if old["body"] != serialized:
                    raise ValueError("Conflicting message ID")
                return dict(json.loads(old["body"]), cursor=old["cursor"])
            row = db.execute("INSERT INTO events(owner,id,session,body) VALUES (?,?,?,?)", (owner, message_id, session, serialized))
            return dict(event, cursor=row.lastrowid)

    def events(self, owner, after=0):
        if type(after) is not int or after < 0:
            raise ValueError("Invalid cursor")
        with self.connect() as db:
            rows = db.execute("SELECT * FROM events WHERE owner=? AND cursor>? ORDER BY cursor LIMIT 50", (owner, after)).fetchall()
        return {"events": [dict(json.loads(r["body"]), cursor=r["cursor"]) for r in rows]}

    def output(self, owner, session, body):
        output = {"id": identifier(body.get("id")), "in_reply_to": identifier(body.get("in_reply_to")),
                  "text": body.get("text"), "shared_context": object_value(body.get("shared_context", {}))}
        if not isinstance(output["text"], str) or len(output["text"]) > 64000:
            raise ValueError("Invalid reply text")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._session(db, owner, session)
            source = db.execute("SELECT body FROM events WHERE owner=? AND id=? AND session=?", (owner, output["in_reply_to"], session)).fetchone()
            if not source:
                raise PermissionError("Reply does not belong to this session")
            if not set(output["shared_context"]).issubset(json.loads(source["body"])["share"]):
                raise PermissionError("Context disclosure was not authorized")
            old = db.execute("SELECT body FROM outputs WHERE owner=? AND (id=? OR reply_to=?)", (owner, output["id"], output["in_reply_to"])).fetchone()
            if old:
                if old["body"] != encoded(output):
                    raise ValueError("Conflicting output")
            else:
                db.execute("INSERT INTO outputs VALUES (?,?,?,?,?)", (owner, output["id"], session, output["in_reply_to"], encoded(output)))
        return output

    def transcript(self, owner, session):
        with self.connect() as db:
            self._session(db, owner, session)
            messages = db.execute("SELECT body FROM events WHERE owner=? AND session=? ORDER BY cursor", (owner, session)).fetchall()
            outputs = db.execute("SELECT body FROM outputs WHERE owner=? AND session=? ORDER BY rowid", (owner, session)).fetchall()
        return {"messages": [json.loads(r[0]) for r in messages], "outputs": [json.loads(r[0]) for r in outputs]}
