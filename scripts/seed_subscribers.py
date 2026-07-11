"""Seed 20 test subscribers: a mix of US (-> SMS) and non-US (-> WhatsApp).

Phones use Twilio 'magic' / test-style numbers where possible. For a real
sandbox send, replace a couple with YOUR verified trial numbers (the US one for
SMS, and a WhatsApp-sandbox-joined number for WhatsApp).

Usage:  python -m scripts.seed_subscribers
"""
from __future__ import annotations

from app.core.phone import validate
from app.db import get_conn, init_db

# (phone, country, name, sms_opt_in, whatsapp_opt_in, language, timezone)
# NOTE: consent is "not yet" collected for real, so most rows are opted-in only
# for sandbox testing. Flip a few opt-ins off to exercise the skip/log path.
SUBSCRIBERS = [
    # --- US -> SMS ---
    ("+12025550101", "US", "Alice (US)",   1, 0, "en", "America/New_York"),
    ("+13105550102", "US", "Ben (US)",     1, 0, "en", "America/Los_Angeles"),
    ("+16175550103", "US", "Carol (US)",   1, 0, "en", "America/New_York"),
    ("+13125550104", "US", "Dan (US)",     1, 0, "en", "America/Chicago"),
    ("+12065550105", "US", "Eve (US)",     0, 0, "en", "America/Los_Angeles"),  # no SMS opt-in -> skip
    ("+14045550106", "US", "Frank (US)",   1, 0, "en", "America/New_York"),
    ("+17135550107", "US", "Grace (US)",   1, 0, "en", "America/Chicago"),
    ("+15125550108", "US", "Heidi (US)",   1, 0, "en", "America/Chicago"),
    # --- Canada (+1 but NOT US) -> WhatsApp (proves we route on stored country) ---
    ("+14165550201", "CA", "Ivan (CA)",    0, 1, "en", "America/Toronto"),
    ("+15145550202", "CA", "Judy (CA)",    0, 1, "fr", "America/Toronto"),
    # --- International -> WhatsApp ---
    ("+447400123456", "GB", "Karl (UK)",   0, 1, "en", "Europe/London"),
    ("+447400123457", "GB", "Lena (UK)",   0, 1, "en", "Europe/London"),
    ("+919812345303", "IN", "Meera (IN)",  0, 1, "en", "Asia/Kolkata"),
    ("+919812345304", "IN", "Nikhil (IN)", 0, 0, "en", "Asia/Kolkata"),        # no WA opt-in -> skip
    ("+61491570305",  "AU", "Olivia (AU)", 0, 1, "en", "Australia/Sydney"),
    ("+4915112345306","DE", "Peter (DE)",  0, 1, "de", "Europe/Berlin"),
    ("+33612345307",  "FR", "Quinn (FR)",  0, 1, "fr", "Europe/Paris"),
    ("+5511987654308","BR", "Rosa (BR)",   0, 1, "pt", "America/Sao_Paulo"),
    ("+819012345309", "JP", "Sato (JP)",   0, 1, "ja", "Asia/Tokyo"),
    ("+27821234310",  "ZA", "Thabo (ZA)",  0, 1, "en", "Africa/Johannesburg"),
]


def main() -> None:
    init_db()
    inserted, skipped = 0, 0
    with get_conn() as conn:
        for phone, country, name, sms, wa, lang, tz in SUBSCRIBERS:
            check = validate(phone)
            if not check.ok:
                print(f"  ! invalid, skipping {phone}: {check.reason}")
                skipped += 1
                continue
            cur = conn.execute(
                """INSERT OR IGNORE INTO subscribers
                   (phone, country, name, sms_opt_in, whatsapp_opt_in, language, timezone, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (check.e164, country, name, sms, wa, lang, tz),
            )
            inserted += cur.rowcount
    print(f"Seeded {inserted} subscribers ({skipped} invalid). Total rows attempted: {len(SUBSCRIBERS)}")


if __name__ == "__main__":
    main()
