"""Preview timezone-aware scheduling for the subscriber list.

Groups active subscribers by timezone (derived from their phone number) and shows
the 10:00-local send schedule as UTC fire times. Computes only - sends nothing.

  python scripts/timezone_preview.py                 # today, 10:00 local
  python scripts/timezone_preview.py 2026-08-01 10   # specific date + hour
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import date as _date

# Allow running as a plain script (python scripts/timezone_preview.py) by putting
# the project root on the path so "app" is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.timezones import resolve_timezone, local_send_time_utc


def main() -> None:
    args = sys.argv[1:]
    target = args[0] if args else _date.today().isoformat()
    hour = int(args[1]) if len(args) > 1 else 10
    y, m, d = (int(x) for x in target.split("-"))

    path = settings.subscribers_csv
    if not os.path.exists(path):
        print(f"Subscriber list not found: {path}")
        print("Set SUBSCRIBERS_CSV, or run from a machine that has the list.")
        return

    groups: dict[str, int] = {}
    unresolved = 0
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("active") != "1":
                continue
            tz = resolve_timezone(r.get("phone_e164", ""))
            if tz:
                groups[tz] = groups.get(tz, 0) + 1
            else:
                unresolved += 1

    total = sum(groups.values())
    print(f"Send date: {target}   Local send time: {hour:02d}:00")
    print(f"Active recipients: {total}   Distinct timezones: {len(groups)}   "
          f"Unresolved: {unresolved}\n")

    rows = []
    for tz, count in groups.items():
        utc_t = local_send_time_utc(tz, y, m, d, hour)
        rows.append((utc_t.strftime("%H:%M"), tz, count))
    rows.sort()

    print(f"{'UTC fire':<11}{'Timezone':<28}{'Recipients':>10}")
    print("-" * 49)
    for utc_t, tz, count in rows:
        print(f"{utc_t:<11}{tz:<28}{count:>10}")
    print("-" * 49)
    print(f"{'':<11}{'TOTAL':<28}{total:>10}")


if __name__ == "__main__":
    main()
