"""Orchestrates a broadcast: load subscribers -> route -> quiet-hours -> send -> log.

Idempotency is enforced two ways:
  * broadcasts.id is deterministic (dedupe on duplicate webhook).
  * deliveries has UNIQUE(broadcast_id, subscriber_id); we INSERT OR IGNORE and
    only send when we actually created the row.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.compliance.quiet_hours import is_within_quiet_window
from app.core import sender
from app.core.router import route
from app.db import get_conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_body(broadcast: dict) -> str:
    parts = [broadcast["title"], "", broadcast["body"]]
    if broadcast.get("link"):
        parts += ["", broadcast["link"]]
    return "\n".join(p for p in parts if p is not None)


def load_recipients(conn, audience: str | None) -> list[dict]:
    """Load active subscribers matching the audience tag (NULL/'all' => everyone)."""
    if not audience or audience.lower() == "all":
        rows = conn.execute("SELECT * FROM subscribers WHERE active = 1").fetchall()
    else:
        # Simple audience match on country for the prototype; extend as needed.
        rows = conn.execute(
            "SELECT * FROM subscribers WHERE active = 1 AND country = ?",
            (audience,),
        ).fetchall()
    return [dict(r) for r in rows]


def run_broadcast(broadcast_id: str) -> dict:
    """Send one broadcast to all matching subscribers. Returns a summary."""
    summary = {"sent": 0, "skipped": 0, "deferred": 0, "duplicate": 0, "failed": 0}
    body_cache: str = ""

    with get_conn() as conn:
        broadcast = conn.execute(
            "SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,)
        ).fetchone()
        if broadcast is None:
            raise ValueError(f"broadcast {broadcast_id} not found")
        broadcast = dict(broadcast)
        body_cache = _render_body(broadcast)

        recipients = load_recipients(conn, broadcast.get("audience"))
        now = datetime.now(timezone.utc)

        for sub in recipients:
            decision = route(sub)

            if not decision.send:
                _record(conn, broadcast_id, sub["id"], decision.channel or "n/a",
                        status="skipped", reason=decision.reason)
                summary["skipped"] += 1
                continue

            # Idempotency claim: create the delivery row first. If it already
            # exists (duplicate webhook / re-run), we do NOT send again.
            claimed = _claim_delivery(conn, broadcast_id, sub["id"], decision.channel)
            if not claimed:
                summary["duplicate"] += 1
                continue

            if is_within_quiet_window(sub.get("timezone", "UTC"), now):
                _update(conn, broadcast_id, sub["id"],
                        status="deferred", reason="quiet hours")
                summary["deferred"] += 1
                continue

            result = sender.send(decision.channel, sub["phone"], body_cache)
            if result.ok:
                _update(conn, broadcast_id, sub["id"],
                        status=result.status, message_sid=result.message_sid,
                        bump_attempt=True)
                summary["sent"] += 1
            else:
                _update(conn, broadcast_id, sub["id"],
                        status="failed", reason=result.error, bump_attempt=True)
                summary["failed"] += 1

    return summary


# --- delivery row helpers -------------------------------------------------

def _claim_delivery(conn, broadcast_id, subscriber_id, channel) -> bool:
    """Insert a queued row iff none exists. Returns True if WE created it."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO deliveries
           (broadcast_id, subscriber_id, channel, status, attempts, updated_at)
           VALUES (?, ?, ?, 'queued', 0, ?)""",
        (broadcast_id, subscriber_id, channel, _now_iso()),
    )
    return cur.rowcount == 1


def _record(conn, broadcast_id, subscriber_id, channel, *, status, reason=None):
    """Insert-or-replace a terminal row (e.g. skipped) that we won't send."""
    conn.execute(
        """INSERT INTO deliveries
             (broadcast_id, subscriber_id, channel, status, reason, attempts, updated_at)
           VALUES (?, ?, ?, ?, ?, 0, ?)
           ON CONFLICT(broadcast_id, subscriber_id) DO UPDATE SET
             status=excluded.status, reason=excluded.reason, updated_at=excluded.updated_at""",
        (broadcast_id, subscriber_id, channel, status, reason, _now_iso()),
    )


def _update(conn, broadcast_id, subscriber_id, *, status,
            message_sid=None, reason=None, bump_attempt=False):
    conn.execute(
        f"""UPDATE deliveries SET
              status = ?,
              message_sid = COALESCE(?, message_sid),
              reason = ?,
              attempts = attempts + {1 if bump_attempt else 0},
              updated_at = ?
            WHERE broadcast_id = ? AND subscriber_id = ?""",
        (status, message_sid, reason, _now_iso(), broadcast_id, subscriber_id),
    )
