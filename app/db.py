"""SQLite connection + schema. Keeps things dependency-light for the prototype."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phone         TEXT NOT NULL UNIQUE,      -- E.164, e.g. +15551234567
    country       TEXT NOT NULL,             -- explicit ISO code; +1 alone is ambiguous (US vs CA)
    name          TEXT,
    sms_opt_in    INTEGER NOT NULL DEFAULT 0,
    whatsapp_opt_in INTEGER NOT NULL DEFAULT 0,
    language      TEXT NOT NULL DEFAULT 'en',
    timezone      TEXT NOT NULL DEFAULT 'UTC',
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id          TEXT PRIMARY KEY,            -- deterministic id => dedupe on double webhook fire
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    link        TEXT,
    audience    TEXT,                        -- optional targeting tag; NULL/'all' => everyone
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    broadcast_id  TEXT NOT NULL,
    subscriber_id INTEGER NOT NULL,
    channel       TEXT NOT NULL,             -- 'sms' | 'whatsapp'
    message_sid   TEXT,                      -- Twilio SID (NULL until sent / in dry-run)
    status        TEXT NOT NULL,             -- queued|sent|delivered|failed|skipped|deferred
    reason        TEXT,                      -- why skipped/failed
    attempts      INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT NOT NULL,
    UNIQUE (broadcast_id, subscriber_id),    -- idempotency: never double-send
    FOREIGN KEY (broadcast_id)  REFERENCES broadcasts(id),
    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
);
"""


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(settings.database_path) or ".", exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
