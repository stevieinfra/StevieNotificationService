"""Sender: SMS goes through Twilio; DRY_RUN returns a fake SID.
(WhatsApp is sent via the Meta Cloud API, not this Twilio sender.)"""
from app.core.router import SMS
from app.core.sender import send


def test_sms_send_dry_run():
    res = send(SMS, "+12025550101", "hello")
    assert res.ok and res.status == "queued"
    assert res.message_sid.startswith("DRYRUN-sms-")
