"""Reset the subscribers table to a SINGLE WhatsApp recipient for a clean
end-to-end pipeline test (so we don't send to the 20 fake seed rows).

The recipient must be a non-US country (so the router picks WhatsApp) and must
have already JOINED the Twilio WhatsApp sandbox.

Usage:
  python -m scripts.setup_wa_test --phone +918328697349 --country IN
"""
from __future__ import annotations

import argparse

from app.core.phone import validate
from app.core.router import WHATSAPP, choose_channel
from app.db import get_conn, init_db


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--phone", required=True, help="sandbox-joined number, E.164")
    p.add_argument("--country", default="IN", help="non-US ISO code so routing -> WhatsApp")
    p.add_argument("--name", default="WA Test")
    args = p.parse_args()

    check = validate(args.phone)
    if not check.ok:
        print(f"ERROR: {args.phone} invalid ({check.reason}).")
        return
    if choose_channel(args.country) != WHATSAPP:
        print(f"ERROR: country {args.country!r} routes to SMS, not WhatsApp. Use a non-US code.")
        return

    init_db()
    with get_conn() as conn:
        # Delete child rows (deliveries) before parents to satisfy FKs.
        # Clearing broadcasts too so re-running the same publish isn't deduped
        # away as a "duplicate" during testing.
        conn.execute("DELETE FROM deliveries")
        conn.execute("DELETE FROM broadcasts")
        conn.execute("DELETE FROM subscribers")
        conn.execute(
            """INSERT INTO subscribers
               (phone, country, name, sms_opt_in, whatsapp_opt_in, language, timezone, active)
               VALUES (?, ?, ?, 0, 1, 'en', 'UTC', 1)""",
            (check.e164, args.country, args.name),
        )
    print(f"Subscribers reset to 1 row: {check.e164} ({args.country}) -> WhatsApp, opted in.")
    print("Now (server running) run:  python -m scripts.simulate_publish")


if __name__ == "__main__":
    main()
