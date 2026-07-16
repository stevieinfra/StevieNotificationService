"""JSON API for the standalone frontend (Vercel).

The static HTML/JS frontend calls these endpoints. Mirrors the schedule form's
logic (config, preview, send) but returns JSON instead of HTML, so the frontend
and backend can live on different hosts (Vercel + Railway/Render).
"""
from __future__ import annotations

import os
import subprocess

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.schedule import (
    TOPICS,
    REMINDER_TYPES,
    _ROOT,
    _load_rows,
    filter_recipients,
    render_body,
)

router = APIRouter(prefix="/api", tags=["api"])


class Campaign(BaseModel):
    body: str = ""
    topics: list[str] = []
    reminder_type: str = ""
    include_unverified: bool = False
    live: bool = False


@router.get("/config")
def config():
    """Topics + reminder types for the form dropdowns/checkboxes."""
    return {
        "topics": [{"code": c, "label": l} for c, l in TOPICS.items()],
        "reminders": REMINDER_TYPES,
    }


@router.post("/preview")
def preview(c: Campaign):
    """Filter the list and return who would receive the message (nothing sent)."""
    rows = _load_rows()
    if rows is None:
        return {"error": f"Subscriber list not found at {settings.subscribers_csv}."}

    matched = filter_recipients(rows, c.topics, c.reminder_type, c.include_unverified)
    samples = [
        {
            "name": r.get("name") or "(no name)",
            "phone": r.get("phone_e164", ""),
            "channel": r.get("channel", ""),
            "message": render_body(c.body, r.get("name", "")),
        }
        for r in matched[:5]
    ]
    return {
        "matched": len(matched),
        "sms": sum(1 for r in matched if r.get("channel") == "sms"),
        "whatsapp": sum(1 for r in matched if r.get("channel") == "whatsapp"),
        "samples": samples,
        "topic_names": [TOPICS.get(t, t) for t in c.topics],
    }


@router.post("/send")
def send(c: Campaign):
    """Run the Node broadcast engine. Dry run unless c.live is true."""
    env = {
        **os.environ,
        "SUBSCRIBERS_CSV": settings.subscribers_csv,
        "BROADCAST_TOPICS": ",".join(c.topics),
        "BROADCAST_REMINDER": c.reminder_type,
        "BROADCAST_INCLUDE_UNVERIFIED": "true" if c.include_unverified else "false",
        "BROADCAST_SMS_BODY": c.body,
        "GAP_SEC": "0",
    }
    args = ["node", "scripts/broadcast.js"] + (["--send"] if c.live else [])
    try:
        proc = subprocess.run(
            args, cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        output = "ERROR: 'node' not found on PATH."
    except subprocess.TimeoutExpired:
        output = "ERROR: send timed out."

    return {"ok": True, "live": c.live, "output": output}
