"""Send ONE real SMS via Twilio to prove your credentials work.
(WhatsApp is sent via the Meta Cloud API — see scripts/sendTemplate.js.)

Prereqs (see console steps in the chat / README):
  * .env has TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN filled in.
  * DRY_RUN=false in .env.
  * TWILIO_SMS_FROM is your Twilio number, and --to is a *verified* number (trial).

Usage:
  python -m scripts.send_test --to +1XXXXXXXXXX
"""
from __future__ import annotations

import argparse

from app.config import settings
from app.core.phone import validate
from app.core.router import SMS
from app.core import sender


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--channel", choices=[SMS], default=SMS)
    p.add_argument("--to", required=True, help="recipient in E.164, e.g. +12025550101")
    p.add_argument("--body", default="Hello from the Stevie Awards broadcast tool test.")
    args = p.parse_args()

    # Guard rails so the failure messages are obvious.
    if settings.dry_run:
        print("DRY_RUN is still true -> nothing will actually send. "
              "Set DRY_RUN=false in .env to do a real send.")
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        print("ERROR: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing in .env.")
        return

    check = validate(args.to)
    if not check.ok:
        print(f"ERROR: {args.to} is not a valid number ({check.reason}).")
        return

    print(f"Sending {args.channel} to {check.e164} ...")
    result = sender.send(args.channel, check.e164, args.body)
    if result.ok:
        print(f"OK  status={result.status}  sid={result.message_sid}")
    else:
        print(f"FAILED: {result.error}")


if __name__ == "__main__":
    main()
