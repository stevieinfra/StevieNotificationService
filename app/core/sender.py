"""Twilio SMS sender.

WhatsApp is sent via the Meta Cloud API (src/messaging/whatsAppSender.js), NOT
through Twilio — so this sender only performs live sends for SMS. In DRY_RUN it
returns a fake SID for any channel so the pipeline stays fully testable.

DRY_RUN=true short-circuits the network call and returns a fake SID so the whole
pipeline is testable without live Twilio credentials.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.core.router import SMS


@dataclass
class SendResult:
    ok: bool
    message_sid: str | None
    status: str            # 'queued' | 'failed'
    error: str | None = None


def _status_callback_url() -> str:
    return f"{settings.public_base_url.rstrip('/')}/webhooks/twilio/status"


def _client():
    # Imported lazily so DRY_RUN works with no twilio creds / package configured.
    from twilio.rest import Client
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def send(channel: str, to_e164: str, body: str) -> SendResult:
    if settings.dry_run:
        fake = f"DRYRUN-{channel}-{abs(hash((to_e164, body))) % 10**10}"
        return SendResult(ok=True, message_sid=fake, status="queued")

    # Live sends go through Twilio for SMS only. WhatsApp is handled by the Meta
    # Cloud API sender (Node), so a live WhatsApp send here is not supported.
    if channel != SMS:
        return SendResult(
            ok=False, message_sid=None, status="failed",
            error="WhatsApp is sent via the Meta Cloud API, not this Twilio sender.",
        )

    try:
        kwargs = dict(from_=settings.twilio_sms_from, to=to_e164, body=body)
        # Twilio only accepts a publicly reachable HTTPS callback. Skip it for
        # local test sends (localhost/http) so a bare send still works.
        if settings.public_base_url.startswith("https://"):
            kwargs["status_callback"] = _status_callback_url()

        msg = _client().messages.create(**kwargs)
        return SendResult(ok=True, message_sid=msg.sid, status=msg.status or "queued")
    except Exception as exc:  # noqa: BLE001 - surface any Twilio error as a failed send
        return SendResult(ok=False, message_sid=None, status="failed", error=str(exc))
