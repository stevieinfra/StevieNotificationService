"""CloudCannon publish webhook: parse -> save broadcast (dedupe) -> broadcast.

We only act on items of type 'broadcast'. The broadcast id is derived
deterministically from a stable source id (or content hash) so that if
CloudCannon fires the webhook twice, we upsert the SAME row and never double-send.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.core.broadcaster import run_broadcast
from app.db import get_conn

router = APIRouter(prefix="/webhooks", tags=["cloudcannon"])


def _derive_id(payload: dict) -> str:
    """Prefer a stable CMS id; fall back to a content hash."""
    stable = payload.get("id") or payload.get("path") or payload.get("slug")
    if stable:
        return f"cc-{hashlib.sha256(str(stable).encode()).hexdigest()[:24]}"
    basis = f"{payload.get('title','')}|{payload.get('body','')}"
    return f"cc-{hashlib.sha256(basis.encode()).hexdigest()[:24]}"


@router.post("/cloudcannon")
async def cloudcannon_publish(
    request: Request,
    x_cc_secret: str | None = Header(default=None, alias="X-CC-Secret"),
):
    # 1. Verify the shared secret.
    if x_cc_secret != settings.cloudcannon_webhook_secret:
        raise HTTPException(status_code=401, detail="bad webhook secret")

    payload = await request.json()

    # 2. Only broadcast-type items trigger a send.
    if payload.get("type") != "broadcast":
        return {"status": "ignored", "reason": f"type={payload.get('type')!r}"}

    broadcast_id = _derive_id(payload)

    # 3. Save (dedupe). If it already exists, we do NOT re-run the send.
    created = False
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO broadcasts (id, title, body, link, audience, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                broadcast_id,
                payload.get("title", "(untitled)"),
                payload.get("body", ""),
                payload.get("link"),
                payload.get("audience"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        created = cur.rowcount == 1

    if not created:
        return {"status": "duplicate", "broadcast_id": broadcast_id}

    # 4. Fan out. (Synchronous for the prototype; move to a task queue for scale.)
    summary = run_broadcast(broadcast_id)
    return {"status": "ok", "broadcast_id": broadcast_id, "summary": summary}
