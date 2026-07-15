"""Schedule New SMS — our own standalone form (prototype).

Mirrors the fields of the reference Drupal form: SMS body, topics, reminder type,
send date/time, and the verified-only consent gate. On submit it filters the
cleaned subscriber list and shows exactly who would receive the message.

Safe by design: it never sends here — it previews the audience + rendered message
(the real send would hand this audience to the notification engine). Wire the
engine call in where marked when you're ready to actually send.
"""
from __future__ import annotations

import csv
import html
import os
import subprocess

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.config import settings

# Project root (…/Stevie_Tool) so we can run the Node broadcast engine from here.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

router = APIRouter(tags=["schedule"])

# Stevie award programs (topic code -> label). Codes match the `topics` column.
TOPICS = {
    "ABA": "American Business Awards",
    "APSA": "Asia-Pacific Stevie Awards",
    "GSA": "German Stevie Awards",
    "IBA": "International Business Awards",
    "MENA": "Middle East & North Africa Stevie Awards",
    "SALES": "Sales & Customer Service",
    "WOMEN": "Women in Business",
    "EMPLOYERS": "Great Employers",
    "SATE": "Technology Excellence",
    "WFC": "Women | Future of Work",
    "IPRA": "Innovation & PR",
    "MENA-AR": "MENA (Arabic)",
}
REMINDER_TYPES = ["First Reminder", "Second Reminder", "Third Reminder", "Final Reminder"]


def _load_rows():
    path = settings.subscribers_csv
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def filter_recipients(rows, topics, reminder_type, include_unverified):
    """Filter subscribers by selected topics + reminder type + consent."""
    sel = set(topics or [])
    out = []
    for r in rows:
        if r.get("active") != "1":  # skip opted-out / inactive
            continue
        row_topics = {t.strip() for t in (r.get("topics") or "").split(";") if t.strip()}
        if sel and not (row_topics & sel):
            continue
        reminders = r.get("reminder_types") or ""
        if reminder_type and reminder_type not in reminders and "All Reminders" not in reminders:
            continue
        verified = (r.get("number_confirmed") or "").lower() == "yes"
        if not include_unverified and not verified:
            continue
        out.append(r)
    return out


def render_body(body: str, name: str) -> str:
    """Fill {name} if used; append the opt-out note (like the real system does)."""
    text = (body or "").replace("{name}", name or "there")
    return f"{text}  Reply STOP to opt out."


# ---------------------------------------------------------------- form page

@router.get("/schedule", response_class=HTMLResponse)
def schedule_form():
    topic_boxes = "".join(
        f'<label class="opt"><input type="checkbox" name="topics" value="{code}"> {html.escape(label)}</label>'
        for code, label in TOPICS.items()
    )
    reminder_opts = "".join(f"<option>{r}</option>" for r in REMINDER_TYPES)
    return f"""
<!doctype html><html><head><meta charset="utf-8"><title>Schedule New SMS</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;max-width:680px;margin:40px auto;color:#1f2d3d;line-height:1.55}}
 h1{{color:#1f3a5f;margin-bottom:26px}} label{{font-weight:600;margin-top:26px;display:block}}
 textarea,select,input[type=date],input[type=time]{{width:100%;padding:10px;margin-top:8px;box-sizing:border-box}}
 .opt{{display:flex;align-items:center;gap:8px;font-weight:400;margin:10px 0}} .opt input{{width:auto;margin:0}}
 .box{{border:1px solid #ccd;border-radius:6px;padding:12px;max-height:180px;overflow:auto;font-weight:400}}
 .row{{display:flex;gap:16px}} .row>div{{flex:1}}
 button{{margin-top:32px;background:#1f3a5f;color:#fff;border:0;padding:12px 22px;border-radius:6px;cursor:pointer;font-size:15px}}
 small{{color:#667}}
</style></head><body>
<h1>Schedule New SMS</h1>
<form method="post" action="/schedule">
  <label>SMS Body *</label>
  <textarea name="body" rows="4" maxlength="120" required
    placeholder="Type your message (120 chars). Use {{name}} to personalize."></textarea>
  <small>Limited to 120 characters — an opt-out line is added automatically. {{name}} is replaced per recipient.</small>

  <label>SMS Topics * <small>(who receives it)</small></label>
  <div class="box">{topic_boxes}</div>

  <label>Reminder Type *</label>
  <select name="reminder_type">{reminder_opts}</select>

  <div class="row">
    <div><label>Date</label><input type="date" name="date"></div>
    <div><label>Time</label><input type="time" name="time"></div>
  </div>

  <label>Include unverified numbers in SMS blast *</label>
  <label class="opt"><input type="radio" name="include_unverified" value="no" checked> No (verified/consented only — recommended)</label>
  <label class="opt"><input type="radio" name="include_unverified" value="yes"> Yes</label>

  <button type="submit">Preview &amp; Schedule</button>
</form></body></html>"""


# ---------------------------------------------------------------- submit

@router.post("/schedule", response_class=HTMLResponse)
def schedule_submit(
    body: str = Form(...),
    topics: list[str] = Form(default=[]),
    reminder_type: str = Form(default=""),
    date: str = Form(default=""),
    time: str = Form(default=""),
    include_unverified: str = Form(default="no"),
):
    rows = _load_rows()
    if rows is None:
        return HTMLResponse(
            f"<p style='color:#b00'>Subscriber list not found at "
            f"<code>{html.escape(settings.subscribers_csv)}</code>. "
            f"Set SUBSCRIBERS_CSV in .env.</p>", status_code=400)

    inc = include_unverified == "yes"
    matched = filter_recipients(rows, topics, reminder_type, inc)

    # channel breakdown
    sms = sum(1 for r in matched if r.get("channel") == "sms")
    wa = sum(1 for r in matched if r.get("channel") == "whatsapp")

    # sample of rendered messages (first 5)
    samples = "".join(
        f"<tr><td>{html.escape(r.get('name') or '(no name)')}</td>"
        f"<td>{html.escape(r.get('phone_e164',''))}</td>"
        f"<td>{r.get('channel','')}</td>"
        f"<td>{html.escape(render_body(body, r.get('name','')))}</td></tr>"
        for r in matched[:5]
    ) or "<tr><td colspan=4>No recipients matched.</td></tr>"

    when = f"{date} {time}".strip() or "immediately"
    topic_names = ", ".join(TOPICS.get(t, t) for t in topics) or "(all topics)"

    # Hidden fields so the confirm/send step re-runs with the exact same campaign.
    hidden = (
        f'<input type="hidden" name="body" value="{html.escape(body)}">'
        f'<input type="hidden" name="reminder_type" value="{html.escape(reminder_type)}">'
        f'<input type="hidden" name="include_unverified" value="{"yes" if inc else "no"}">'
        + "".join(
            f'<input type="hidden" name="topics" value="{html.escape(t)}">' for t in topics
        )
    )

    return HTMLResponse(f"""
<!doctype html><html><head><meta charset="utf-8"><title>Scheduled</title>
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:820px;margin:30px auto;color:#1f2d3d}}
 h1{{color:#1f3a5f}} table{{border-collapse:collapse;width:100%;margin-top:10px;font-size:13px}}
 td,th{{border:1px solid #dde;padding:6px;text-align:left}} th{{background:#eef2f7}}
 .stat{{display:inline-block;background:#eef2f7;border-radius:6px;padding:8px 14px;margin:6px 8px 0 0}}
 .note{{background:#fff7e6;border:1px solid #f0d9a8;padding:12px;border-radius:6px;margin-top:20px;line-height:1.5}}</style>
</head><body>
<h1>Preview</h1>
<p><b>Topics:</b> {html.escape(topic_names)} &nbsp; | &nbsp;
   <b>Reminder:</b> {html.escape(reminder_type)} &nbsp; | &nbsp;
   <b>When:</b> {html.escape(when)} &nbsp; | &nbsp;
   <b>Unverified included:</b> {"Yes" if inc else "No"}</p>

<div class="stat"><b>{len(matched)}</b> recipients matched</div>
<div class="stat">SMS (US): <b>{sms}</b></div>
<div class="stat">WhatsApp (intl): <b>{wa}</b></div>

<h3>Sample messages (first 5)</h3>
<table><tr><th>Name</th><th>Number</th><th>Channel</th><th>Message</th></tr>{samples}</table>

<div class="note"><b>Nothing sent yet — this is the preview.</b> Confirm below to send.
Leave the box unchecked for a safe dry run (logs what would send); check it to send for real.</div>

<form method="post" action="/schedule/send" style="margin-top:16px">
  {hidden}
  <label style="font-weight:400;display:block;margin-bottom:10px">
    <input type="checkbox" name="live" value="yes"> <b>Send for real (live)</b>
  </label>
  <button type="submit" style="background:#1f3a5f;color:#fff;border:0;padding:10px 18px;border-radius:6px;cursor:pointer">Send now</button>
</form>
<p style="margin-top:14px"><a href="/schedule">← Schedule another</a></p>
</body></html>""")


# ---------------------------------------------------------------- send (runs the engine)

@router.post("/schedule/send", response_class=HTMLResponse)
def schedule_send(
    body: str = Form(...),
    topics: list[str] = Form(default=[]),
    reminder_type: str = Form(default=""),
    include_unverified: str = Form(default="no"),
    live: str = Form(default=""),
):
    """Run the Node broadcast engine with the chosen campaign. Dry run unless live."""
    inc = include_unverified == "yes"
    is_live = live == "yes"

    env = {
        **os.environ,
        "SUBSCRIBERS_CSV": settings.subscribers_csv,
        "BROADCAST_TOPICS": ",".join(topics),
        "BROADCAST_REMINDER": reminder_type,
        "BROADCAST_INCLUDE_UNVERIFIED": "true" if inc else "false",
        "BROADCAST_SMS_BODY": body,
        "GAP_SEC": "0",  # no inter-send delay so the HTTP request doesn't hang
    }
    args = ["node", "scripts/broadcast.js"] + (["--send"] if is_live else [])
    try:
        proc = subprocess.run(
            args, cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        output = "ERROR: 'node' was not found on PATH. Install Node.js to run the send engine."
    except subprocess.TimeoutExpired:
        output = "ERROR: send timed out (audience too large for a synchronous run)."

    mode = "LIVE — messages were sent" if is_live else "DRY RUN — nothing was sent"
    color = "#b00" if is_live else "#1f3a5f"
    return HTMLResponse(f"""
<!doctype html><html><head><meta charset="utf-8"><title>Send result</title>
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:820px;margin:30px auto;color:#1f2d3d}}
 h1{{color:{color}}} pre{{background:#0f1b2d;color:#e6edf5;padding:14px;border-radius:8px;overflow:auto;font-size:12px;line-height:1.5}}</style>
</head><body>
<h1>{mode}</h1>
<p>Ran the broadcast engine{" (LIVE)" if is_live else " in dry run"}. Engine output:</p>
<pre>{html.escape(output) or "(no output)"}</pre>
<p><a href="/schedule">← Schedule another</a></p>
</body></html>""")
