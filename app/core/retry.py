"""Retry failed deliveries with exponential backoff.

Backoff schedule (attempt -> minimum minutes since last update before retry):
  1 -> 1 min, 2 -> 5 min, 3 -> 30 min. After MAX_ATTEMPTS we give up.
Call retry_failed() from a scheduler/cron; it re-sends eligible rows.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core import sender
from app.db import get_conn

MAX_ATTEMPTS = 3
BACKOFF_MINUTES = {1: 1, 2: 5, 3: 30}


def _eligible(row, now: datetime) -> bool:
    if row["attempts"] >= MAX_ATTEMPTS:
        return False
    wait = BACKOFF_MINUTES.get(row["attempts"], 30)
    last = datetime.fromisoformat(row["updated_at"])
    return (now - last).total_seconds() >= wait * 60


def retry_failed() -> dict:
    summary = {"retried": 0, "recovered": 0, "gave_up": 0}
    now = datetime.now(timezone.utc)

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT d.*, s.phone FROM deliveries d "
            "JOIN subscribers s ON s.id = d.subscriber_id "
            "WHERE d.status = 'failed'"
        ).fetchall()

        for row in rows:
            if row["attempts"] >= MAX_ATTEMPTS:
                summary["gave_up"] += 1
                continue
            if not _eligible(row, now):
                continue

            summary["retried"] += 1
            body = _reconstruct_body(conn, row["broadcast_id"])
            result = sender.send(row["channel"], row["phone"], body)
            status = result.status if result.ok else "failed"
            conn.execute(
                "UPDATE deliveries SET status=?, message_sid=COALESCE(?, message_sid), "
                "reason=?, attempts=attempts+1, updated_at=? WHERE id=?",
                (status, result.message_sid, result.error,
                 now.isoformat(), row["id"]),
            )
            if result.ok:
                summary["recovered"] += 1

    return summary


def _reconstruct_body(conn, broadcast_id: str) -> str:
    b = conn.execute("SELECT * FROM broadcasts WHERE id=?", (broadcast_id,)).fetchone()
    parts = [b["title"], "", b["body"]]
    if b["link"]:
        parts += ["", b["link"]]
    return "\n".join(p for p in parts if p is not None)
