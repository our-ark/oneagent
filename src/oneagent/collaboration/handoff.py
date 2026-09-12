"""Scoped, expiring browser handoffs for an authenticated channel principal.

The host authenticates the principal before calling account(). Raw channel IDs
and bearer tokens are never persisted. Each application gets its own cookie.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import secrets
import sqlite3
import time


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class HandoffStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts(principal TEXT PRIMARY KEY, owner TEXT, active INTEGER);
                CREATE TABLE IF NOT EXISTS handoffs(token TEXT PRIMARY KEY, owner TEXT, app TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS browsers(token TEXT PRIMARY KEY, owner TEXT, app TEXT, csrf TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS channels(owner TEXT, app TEXT, session TEXT, PRIMARY KEY(owner,app));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            with db:
                yield db
        finally:
            db.close()

    def account(self, principal, *, start=False, reset=False, include_inactive=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            key = digest(principal)
            row = db.execute("SELECT owner,active FROM accounts WHERE principal=?", (key,)).fetchone()
            if not start:
                return row[0] if row and (row[1] or include_inactive) else None
            if reset and row:
                db.execute("DELETE FROM handoffs WHERE owner=?", (row[0],))
                db.execute("DELETE FROM browsers WHERE owner=?", (row[0],))
            owner = row[0] if row and not reset else secrets.token_hex(32)
            db.execute("INSERT INTO accounts VALUES (?,?,1) ON CONFLICT(principal) DO UPDATE SET owner=excluded.owner, active=1", (key, owner))
            return owner

    def stop(self, principal):
        with self.connect() as db:
            db.execute("UPDATE accounts SET active=0 WHERE principal=?", (digest(principal),))

    def linked(self, owner):
        with self.connect() as db:
            return bool(db.execute("SELECT 1 FROM accounts WHERE owner=?", (owner,)).fetchone())

    def issue(self, owner, app, *, ttl=900):
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute("DELETE FROM handoffs WHERE expires<=?", (time.time(),))
            db.execute("INSERT INTO handoffs VALUES (?,?,?,?)", (digest(token), owner, app, time.time() + ttl))
        return token

    def redeem(self, token, app):
        if not isinstance(token, str) or not 20 <= len(token) <= 100:
            raise PermissionError("Invalid connection link. Request new links with /traveldemo.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT owner FROM handoffs WHERE token=? AND app=? AND expires>?", (digest(token), app, time.time())).fetchone()
            if not row:
                raise PermissionError("This connection link expired or was already used. Request new links with /traveldemo.")
            db.execute("DELETE FROM handoffs WHERE token=?", (digest(token),))
            return self._browser(db, row[0], app)

    def _browser(self, db, owner, app):
        token, csrf = secrets.token_hex(32), secrets.token_hex(32)
        db.execute("INSERT INTO browsers VALUES (?,?,?,?,?)", (digest(token), owner, app, csrf, time.time() + 86400))
        return owner, csrf, token

    def browser(self, token, app, *, allow_new=True):
        with self.connect() as db:
            row = db.execute("SELECT owner,csrf FROM browsers WHERE token=? AND app=? AND expires>?", (digest(token), app, time.time())).fetchone()
            if row:
                return row[0], row[1], None
            if token and not allow_new:
                raise PermissionError("Your trip session expired or was reset. Open fresh links from /traveldemo.")
            return self._browser(db, secrets.token_hex(32), app)

    def channel(self, owner, app, create):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT session FROM channels WHERE owner=? AND app=?", (owner, app)).fetchone()
            if row:
                return row[0]
            session = create()["session_id"]
            db.execute("INSERT INTO channels VALUES (?,?,?)", (owner, app, session))
            return session
