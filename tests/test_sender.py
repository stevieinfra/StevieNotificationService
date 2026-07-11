"""Sender formatting: WhatsApp gets the prefix, SMS does not. DRY_RUN => fake SID."""
from app.core.router import SMS, WHATSAPP
from app.core.sender import send


def test_sms_send_dry_run():
    res = send(SMS, "+12025550101", "hello")
    assert res.ok and res.status == "queued"
    assert res.message_sid.startswith("DRYRUN-sms-")


def test_whatsapp_send_dry_run():
    res = send(WHATSAPP, "+919812345303", "hello")
    assert res.ok and res.status == "queued"
    assert res.message_sid.startswith("DRYRUN-whatsapp-")
