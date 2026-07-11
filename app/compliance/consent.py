"""STOP / HELP handling and consent persistence (TCPA).

Twilio's Advanced Opt-Out can auto-handle STOP for SMS, but we ALSO update our
own subscriber record so routing/opt-in stays authoritative in our DB, and we
handle WhatsApp (where Twilio does not manage opt-out for us).
"""
from __future__ import annotations

from app.core.router import SMS, WHATSAPP

STOP_KEYWORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
HELP_KEYWORDS = {"help", "info"}
START_KEYWORDS = {"start", "yes", "unstop"}

HELP_REPLY = (
    "Stevie Awards alerts. Msg&data rates may apply. "
    "Reply STOP to unsubscribe. Support: help@stevieawards.com"
)
STOP_REPLY = "You are unsubscribed from Stevie Awards alerts. Reply START to rejoin."
START_REPLY = "You are re-subscribed to Stevie Awards alerts. Reply STOP to opt out."


def classify_inbound(body: str) -> str | None:
    """Return 'stop' | 'help' | 'start' | None for an inbound message body."""
    word = (body or "").strip().lower()
    if word in STOP_KEYWORDS:
        return "stop"
    if word in HELP_KEYWORDS:
        return "help"
    if word in START_KEYWORDS:
        return "start"
    return None


def opt_in_column(channel: str) -> str:
    return "sms_opt_in" if channel == SMS else "whatsapp_opt_in"
