"""Twilio sender for both SMS and WhatsApp.

SMS  -> plain E.164 'to'/'from'.
WhatsApp -> 'whatsapp:' prefix on both, and in production an approved template.
In the sandbox a plain body works, so we support both.

DRY_RUN=true short-circuits the network call and returns a fake SID so the whole
pipeline is testable without live Twilio credentials.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.core.router import SMS, WHATSAPP


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
    from_addr = settings.twilio_sms_from if channel == SMS else settings.twilio_whatsapp_from
    to_addr = to_e164
    if channel == WHATSAPP:
        from_addr = f"whatsapp:{from_addr}"
        to_addr = f"whatsapp:{to_e164}"

    if settings.dry_run:
        fake = f"DRYRUN-{channel}-{abs(hash((to_e164, body))) % 10**10}"
        return SendResult(ok=True, message_sid=fake, status="queued")

    try:
        kwargs = dict(from_=from_addr, to=to_addr)
        # Twilio only accepts a publicly reachable HTTPS callback. Skip it for
        # local test sends (localhost/http) so a bare send still works.
        if settings.public_base_url.startswith("https://"):
            kwargs["status_callback"] = _status_callback_url()
        # Production WhatsApp: use an approved content template instead of raw body.
        if channel == WHATSAPP and settings.twilio_whatsapp_template_sid:
            kwargs["content_sid"] = settings.twilio_whatsapp_template_sid
        else:
            kwargs["body"] = body

        msg = _client().messages.create(**kwargs)
        return SendResult(ok=True, message_sid=msg.sid, status=msg.status or "queued")
    except Exception as exc:  # noqa: BLE001 - surface any Twilio error as a failed send
        return SendResult(ok=False, message_sid=None, status="failed", error=str(exc))
