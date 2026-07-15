# Stevie Notification Tool

Sends Stevie Awards notifications to subscribers, routing by **country**:
**US → SMS (Twilio)**, **everywhere else → WhatsApp (Meta Cloud API)**.
Messages are filtered by program (topic), reminder type, and consent.

## Two parts

**1. Messaging + broadcast (Node)** — the piece that actually sends.
- `src/messaging/` — channel-agnostic sender facade
  - `twilioSmsSender.js` — SMS via Twilio
  - `whatsAppSender.js` — WhatsApp via Meta Cloud API (approved templates)
  - `messenger.js` — `sendMessage(channel, to, payload)`, builds each sender lazily
- `src/subscribers.js` — load + filter the subscriber list (topic / reminder / consent)
- `scripts/broadcast.js` — **the MVP**: filter a list and send over the right channel

**2. Schedule form (Python / FastAPI)** — the audience-picker UI.
- `app/schedule.py` — a "Schedule New SMS" form: compose a message, pick program +
  reminder + consent, **preview** exactly who would receive it, then **Send**
  (dry run by default; tick "Send for real" to go live). The send step runs the
  Node broadcast engine (`scripts/broadcast.js`) under the hood.
- `app/webhooks/twilio.py` — Twilio delivery-status + STOP/HELP inbound handling.

> Note: the Node side is what has been proven end-to-end (real SMS + WhatsApp
> delivered). The Python `app/core/*` sender is an earlier implementation kept for
> the form/tests; the two stacks should eventually converge.

## Quick start

```bash
# --- Node (sending) ---
npm install
cp .env.example .env          # fill in Twilio + WhatsApp creds; DRY_RUN safe by default

# Broadcast (DRY RUN — shows who + what, sends nothing):
BROADCAST_TOPIC=IBA BROADCAST_REMINDER="First Reminder" npm run broadcast
# Actually send:
BROADCAST_TOPIC=IBA npm run broadcast -- --send

# Single WhatsApp template test:
WA_TEMPLATE=stevie_entry_confirmation WA_VARS="Vennela|American Business Awards|https://stevieawards.com" npm run wa:send

# --- Python (schedule form) ---
pip install -r requirements.txt
SUBSCRIBERS_CSV=fixtures/sample_subscribers.csv uvicorn app.main:app --reload
# open http://localhost:8000/schedule
```

`fixtures/sample_subscribers.csv` is a small **fake** list for safe testing. Point
`SUBSCRIBERS_CSV` at the real cleaned list when ready.

## WhatsApp templates

Business-initiated WhatsApp requires **pre-approved templates** (created in Meta's
WhatsApp Manager). One template with variables (`{{1}} {{2}} …`) serves all
programs/recipients. Categories matter:
- **Utility** (confirmations, status) → delivers reliably.
- **Marketing** (promotional reminders) → Meta frequency-caps per user; delivers
  best to engaged/opted-in users.

## Consent & compliance

- Only **verified / opted-in** subscribers are targeted by default.
- SMS: STOP/HELP handled via the Twilio inbound webhook.
- Country is **stored**, never inferred from the dial code.

## Deferred to production (business/admin)

- **Permanent WhatsApp token** (System User) — the temporary token expires hourly.
- **Verified WhatsApp sender** — currently a Meta test number (max 5 recipients),
  and messages show as the sending business, not "Stevie Awards".
- **A2P 10DLC** registration for US SMS at scale.
- Real subscriber list + a scheduler for large fan-out.
