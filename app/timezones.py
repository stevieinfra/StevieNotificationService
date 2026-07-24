"""Timezone resolution for scheduling.

Derives each recipient's timezone from their phone number, groups recipients by
timezone, and computes the exact UTC instant for a local send time (e.g. 10:00
local). This is the foundation for timezone-aware scheduling: one campaign can be
split into per-timezone sends, each firing at the chosen local hour.

Pure computation — nothing is sent here.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import phonenumbers
from phonenumbers import timezone as _pntz

UTC = ZoneInfo("UTC")


def resolve_timezone(phone_e164: str) -> str | None:
    """Return the IANA timezone (e.g. 'Asia/Kolkata') for a phone number.

    Uses the number itself, so multi-timezone countries (US, Australia) resolve by
    area code where possible. Returns None if the number can't be parsed/resolved.
    """
    try:
        num = phonenumbers.parse(phone_e164, None)
        zones = _pntz.time_zones_for_number(num)
        return zones[0] if zones else None
    except Exception:
        return None


def group_by_timezone(recipients, phone_key: str = "phone_e164"):
    """Group recipient dicts by resolved timezone.

    Returns (groups, unresolved):
      groups     -> {timezone: [recipient, ...]}
      unresolved -> [recipient, ...] whose timezone could not be determined
    """
    groups: dict[str, list] = {}
    unresolved: list = []
    for r in recipients:
        tz = resolve_timezone(r.get(phone_key, ""))
        if tz:
            groups.setdefault(tz, []).append(r)
        else:
            unresolved.append(r)
    return groups, unresolved


def local_send_time_utc(timezone: str, year: int, month: int, day: int,
                        hour: int = 10, minute: int = 0) -> datetime:
    """The UTC datetime corresponding to hour:minute LOCAL time in `timezone`
    on the given date. Daylight saving is handled by the timezone database.

    e.g. 10:00 in 'Asia/Kolkata' on 2026-08-01 -> 04:30 UTC.
    """
    local = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(timezone))
    return local.astimezone(UTC)
