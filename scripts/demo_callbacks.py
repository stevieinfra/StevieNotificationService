"""Demonstrate Twilio status callback + inbound STOP against the running app.

Usage: python -m scripts.demo_callbacks
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.db import get_conn

BASE = settings.public_base_url.rstrip("/")


def _optin_state(phone: str) -> tuple[int, int]:
    with get_conn() as c:
        r = c.execute(
            "SELECT sms_opt_in, whatsapp_opt_in FROM subscribers WHERE phone=?",
            (phone,),
        ).fetchone()
    return (r["sms_opt_in"], r["whatsapp_opt_in"])


def _status_of(sid: str) -> str | None:
    with get_conn() as c:
        r = c.execute("SELECT status FROM deliveries WHERE message_sid=?", (sid,)).fetchone()
    return r["status"] if r else None


def main() -> None:
    with get_conn() as c:
        row = c.execute("SELECT message_sid FROM deliveries WHERE status='queued' LIMIT 1").fetchone()
    sid = row["message_sid"]

    with httpx.Client(timeout=15) as client:
        # 1) Status callback: queued -> delivered
        print(f"[status] {sid}  before={_status_of(sid)}")
        client.post(f"{BASE}/webhooks/twilio/status",
                    data={"MessageSid": sid, "MessageStatus": "delivered"})
        print(f"[status] {sid}  after ={_status_of(sid)}")

        # 2) Inbound STOP (SMS) -> opt out
        phone = "+919812345303"
        print(f"\n[STOP] {phone} opt-in before (sms, wa) = {_optin_state(phone)}")
        r = client.post(f"{BASE}/webhooks/twilio/inbound",
                        data={"From": phone, "Body": "STOP"})
        print(f"[STOP] reply TwiML: {r.text}")
        print(f"[STOP] {phone} opt-in after  (sms, wa) = {_optin_state(phone)}")

        # 3) Inbound START -> opt back in
        r = client.post(f"{BASE}/webhooks/twilio/inbound",
                        data={"From": phone, "Body": "START"})
        print(f"\n[START] reply TwiML: {r.text}")
        print(f"[START] {phone} opt-in after (sms, wa) = {_optin_state(phone)}")


if __name__ == "__main__":
    main()
