# Stevie Notification Tool — Handover

A tool to send Stevie Awards notifications to subscribers over **SMS (US) and
WhatsApp (international)**, filtered by program, reminder type, and consent.

## What's working (tested)
- **SMS** sending via Twilio — proven with real delivery.
- **WhatsApp** sending via Meta Cloud API — proven; 5 Stevie templates approved.
- **Broadcast engine** (`scripts/broadcast.js`) — filters the list and sends over the
  right channel, personalized.
- **Schedule form** (`/schedule`) — compose → preview the audience → send. Runs the
  broadcast engine under the hood. Dry-run by default; a checkbox sends for real.

## How to test it (NO credentials needed) ✅
The whole logic runs in **dry run** with no accounts — start here.

```bash
npm install
pip install -r requirements.txt

# 1) Broadcast engine, dry run (prints who + what, sends nothing):
BROADCAST_TOPIC=IBA BROADCAST_REMINDER="First Reminder" npm run broadcast

# 2) Schedule form (UI):
SUBSCRIBERS_CSV=fixtures/sample_subscribers.csv uvicorn app.main:app --reload
#   open http://localhost:8000/schedule  -> fill in -> Preview -> Send now (dry run)
```

`fixtures/sample_subscribers.csv` is a small **fake** list included for testing.

## How to send for real (needs credentials)
1. Copy `.env.example` → `.env` and fill in:
   - Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
   - WhatsApp: `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_WABA_ID`
2. For WhatsApp testing, add recipient numbers as verified test recipients in Meta,
   or use the production verified sender.
3. Run with the live flag: `npm run broadcast -- --send`, or tick "Send for real"
   in the form.

## What the team still needs to do (business side — not code)
1. **Permanent WhatsApp token** — the temporary token expires ~hourly. Create a
   System User token in Business Settings (needs business admin).
2. **Verified WhatsApp sender** — currently a Meta test number (max 5 recipients),
   and messages show as "Flashback Inc", not "Stevie Awards".
3. **A2P 10DLC** registration for US SMS at scale.
4. Point `SUBSCRIBERS_CSV` at the **real cleaned list** (kept out of git — PII).
5. Confirm the real **message wording + entry links** with marketing.

## Notes
- WhatsApp business-initiated messages must use **pre-approved templates**.
  Utility templates (confirmations, status) deliver reliably; Marketing
  (promotional reminders) is frequency-capped by Meta and delivers best to
  opted-in/engaged users.
- Two stacks: Node (`src/`, `scripts/`) does the sending; Python (`app/`) hosts the
  form. See `README.md` for details.
- The form send runs synchronously — fine for testing; a large real blast should
  run as a background job.
