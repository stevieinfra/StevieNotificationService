"""Channel routing + opt-in enforcement.

Rule: recipients in the US get SMS; everyone else gets WhatsApp. Country is the
STORED subscriber country (ISO code), never inferred from the +1 dial code
(US and Canada share +1).
"""
from __future__ import annotations

from dataclasses import dataclass

SMS = "sms"
WHATSAPP = "whatsapp"


@dataclass
class RouteDecision:
    channel: str            # 'sms' | 'whatsapp'
    send: bool              # False => skip this subscriber
    reason: str | None = None


def choose_channel(country: str) -> str:
    """US => SMS, everywhere else => WhatsApp."""
    return SMS if (country or "").strip().upper() == "US" else WHATSAPP


def route(subscriber: dict) -> RouteDecision:
    """Decide channel for a subscriber row and whether we're allowed to send."""
    if not subscriber.get("active", 1):
        return RouteDecision(channel="", send=False, reason="subscriber inactive")

    channel = choose_channel(subscriber.get("country", ""))

    if channel == SMS and not subscriber.get("sms_opt_in"):
        return RouteDecision(channel=SMS, send=False, reason="no SMS opt-in")
    if channel == WHATSAPP and not subscriber.get("whatsapp_opt_in"):
        return RouteDecision(channel=WHATSAPP, send=False, reason="no WhatsApp opt-in")

    return RouteDecision(channel=channel, send=True)
