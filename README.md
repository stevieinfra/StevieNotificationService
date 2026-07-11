# Stevie Broadcast Tool

Sends Stevie Awards updates to subscribers, routing by **country**:
**US → SMS, everywhere else → WhatsApp**. Content is authored in CloudCannon;
**publishing** a `type: broadcast` item fires a webhook that triggers the send.

One provider (**Twilio**) handles both channels.

## Pipeline

```
CloudCannon publish
   └─ POST /webhooks/cloudcannon   (verify secret, type==broadcast)
        └─ parse + save broadcasts row (deterministic id => dedupe)
             └─ broadcaster: load subscribers
                  └─ router: country=="US" ? SMS : WhatsApp   (skip if no opt-in)
                       └─ quiet-hours check (per timezone)
                            └─ sender: Twilio SMS / whatsapp: prefix
                                 └─ deliveries row (message_sid, status)

Twilio delivery status  -> POST /webhooks/twilio/status  (update row; retry failures w/ backoff)
Inbound STOP/HELP/START -> POST /webhooks/twilio/inbound  (update consent, auto-reply)
```

## Data model

- **subscribers**(phone, country, name, sms_opt_in, whatsapp_opt_in, language, timezone, active)
- **broadcasts**(id, title, body, link, audience, created_at)
- **deliveries**(id, broadcast_id, subscriber_id, channel, message_sid, status, reason, attempts, updated_at)
  - `UNIQUE(broadcast_id, subscriber_id)` enforces **never double-send**.

## Quick start (sandbox, no live Twilio needed)

```bash
python -m venv .venv && . .venv/Scripts/activate    # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                 # DRY_RUN=true by default

python -m scripts.seed_subscribers                   # 20 test subs (US + intl)
uvicorn app.main:app --reload                        # in one terminal
python -m scripts.simulate_publish --duplicate       # in another: fire (twice => dedupe)
pytest -q                                            # unit + e2e tests
```

In `DRY_RUN=true`, sends are logged with a fake `DRYRUN-...` SID — the whole flow
works without Twilio credentials.

## Going live (after the sandbox flow is proven)

1. Set real `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM`, and set `DRY_RUN=false`.
2. Expose the app publicly (ngrok) and set `PUBLIC_BASE_URL`; point Twilio's
   status callback + inbound webhook at `/webhooks/twilio/status` and `/webhooks/twilio/inbound`.
3. **WhatsApp**: join the Twilio WhatsApp sandbox, then before production create a
   Meta-**approved template** and set `TWILIO_WHATSAPP_TEMPLATE_SID`. Business-initiated
   WhatsApp requires the template **and** prior opt-in.
4. **US SMS**: register **A2P 10DLC** or carriers will filter your traffic.
5. Verify **STOP/HELP** replies and consent persistence on both channels.

## Compliance built in

- Consent stored per channel; **STOP/HELP/START** honored automatically (TCPA).
- Idempotency at both the broadcast and per-recipient level.
- **Quiet hours** enforced per recipient timezone (deferred, not dropped).
- Country is **stored**, never inferred from the dial code (US and Canada share +1).
- Retry with exponential backoff on failed deliveries (`POST /admin/retry`).

## Not wired up yet (deliberately deferred)

Real recipient list, 10DLC registration, approved WhatsApp templates, and a task
queue/scheduler for large fan-out + automatic retry cron.
```
