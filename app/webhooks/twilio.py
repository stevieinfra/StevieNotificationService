"""Twilio webhooks: delivery status callbacks + inbound STOP/HELP.

Status callback  -> update the matching deliveries row by MessageSid.
Inbound message  -> classify STOP/HELP/START, update consent, auto-reply (TwiML).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Form, Response

from app.compliance import consent
from app.core.router import WHATSAPP
from app.db import get_conn

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


@router.post("/status")
async def status_callback(
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    ErrorCode: str | None = Form(default=None),
):
    """Twilio posts delivered/sent/failed/undelivered here per message."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE deliveries SET status=?, reason=?, updated_at=? WHERE message_sid=?",
            (MessageStatus, ErrorCode, datetime.now(timezone.utc).isoformat(), MessageSid),
        )
    return {"status": "ok"}


def _twiml(message: str | None) -> Response:
    if message is None:
        body = "<Response/>"
    else:
        body = f"<Response><Message>{message}</Message></Response>"
    return Response(content=body, media_type="application/xml")


@router.post("/inbound")
async def inbound(
    From: str = Form(...),           # e.g. '+15551234567' or 'whatsapp:+91...'
    Body: str = Form(default=""),
):
    """Handle STOP/HELP/START. Update our consent record and auto-reply."""
    action = consent.classify_inbound(Body)

    # Normalize 'whatsapp:+..' -> channel + bare E.164
    channel = WHATSAPP if From.startswith("whatsapp:") else "sms"
    phone = From.replace("whatsapp:", "")
    col = consent.opt_in_column(channel)

    if action == "stop":
        with get_conn() as conn:
            conn.execute(f"UPDATE subscribers SET {col}=0 WHERE phone=?", (phone,))
        return _twiml(consent.STOP_REPLY)

    if action == "start":
        with get_conn() as conn:
            conn.execute(f"UPDATE subscribers SET {col}=1 WHERE phone=?", (phone,))
        return _twiml(consent.START_REPLY)

    if action == "help":
        return _twiml(consent.HELP_REPLY)

    # No keyword matched — stay silent (or route to support later).
    return _twiml(None)
