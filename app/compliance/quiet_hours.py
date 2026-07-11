"""Quiet-hours check per recipient timezone (TCPA-friendly).

Returns whether it's OK to send *right now* in the recipient's local time.
Deferred sends are marked 'deferred' in deliveries and can be picked up later.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings


def is_within_quiet_window(timezone: str, now_utc: datetime) -> bool:
    """True if the current recipient-local hour is OUTSIDE allowed hours."""
    try:
        tz = ZoneInfo(timezone or "UTC")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")

    local_hour = now_utc.astimezone(tz).hour
    start, end = settings.quiet_hours_start, settings.quiet_hours_end
    # Allowed window is [start, end). Anything else is "quiet".
    allowed = start <= local_hour < end
    return not allowed
