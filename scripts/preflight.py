"""Check the tool is configured for a REAL send, without revealing secrets.

Usage: python -m scripts.preflight
"""
from __future__ import annotations

from app.config import settings


def _mask(v: str) -> str:
    if not v:
        return "(empty)"
    return f"{v[:4]}...{v[-2:]} (len {len(v)})"


def main() -> None:
    print("Config readiness:")
    print(f"  DRY_RUN               = {settings.dry_run}  "
          f"{'<-- still TRUE: nothing will actually send' if settings.dry_run else '(real sends ON)'}")
    print(f"  TWILIO_ACCOUNT_SID    = {_mask(settings.twilio_account_sid)}  "
          f"{'OK' if settings.twilio_account_sid.startswith('AC') else '<-- should start with AC'}")
    print(f"  TWILIO_AUTH_TOKEN     = {_mask(settings.twilio_auth_token)}")
    print(f"  TWILIO_WHATSAPP_FROM  = {settings.twilio_whatsapp_from}")
    print(f"  TWILIO_SMS_FROM       = {settings.twilio_sms_from or '(empty - only needed for SMS)'}")
    print(f"  QUIET_HOURS           = {settings.quiet_hours_start}:00 - {settings.quiet_hours_end}:00 "
          f"(recipient local time; sends outside are deferred)")
    print(f"  PUBLIC_BASE_URL       = {settings.public_base_url}")

    ready = (not settings.dry_run
             and settings.twilio_account_sid.startswith("AC")
             and bool(settings.twilio_auth_token))
    print()
    print("READY for a real WhatsApp send." if ready
          else "NOT ready - fix the items marked above.")


if __name__ == "__main__":
    main()
