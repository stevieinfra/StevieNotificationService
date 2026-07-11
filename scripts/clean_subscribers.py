"""Clean the raw CloudCannon/Stevie SMS subscriber export into useful data.

What it does
------------
1. Splits `mobile_number` (dialing code glued to the number) into:
     country_code (e.g. 91), national_number, and a validated E.164 phone.
2. Normalizes `country` -> ISO-3166 alpha-2 (fixes full names + blanks).
3. Repairs mojibake names (UTF-8 that was mis-decoded as Windows-1252).
4. Flags junk: bot-signup spam, SQL/XSS injection, email/numeric/empty names,
   invalid phones, and duplicate people (same phone).
5. Maps number_confirmed / opt_out -> consent + active, and routes each
   subscriber to a channel (US -> SMS, else WhatsApp) to match the tool.

Outputs two files next to the input:
   <name>.cleaned.csv   - valid, deduped, ready-to-use rows
   <name>.review.csv    - everything rejected, with a `reason` column

Usage:
   python -m scripts.clean_subscribers "path/to/SMS subscribers export.csv"
   python -m scripts.clean_subscribers input.csv --encoding utf-8
"""
from __future__ import annotations

import argparse
import csv
import os
import re
from datetime import datetime

import phonenumbers

try:
    import ftfy  # purpose-built mojibake repair (handles Thai/Arabic/double-encoding)
except ImportError:
    ftfy = None

# --- country full-name -> ISO alpha-2 (only the ones that appear as names) ---
NAME_TO_ISO = {
    "malaysia": "MY", "india": "IN", "china": "CN", "australia": "AU",
    "bangladesh": "BD", "united states": "US", "uk": "GB",
    "united kingdom": "GB", "uae": "AE",
}

# Injection / XSS / SQL fingerprints (checked against raw name + phone).
INJECTION_RE = re.compile(
    r"(<\s*div|<\s*script|http[s]?://|waitfor\s+delay|%00|"
    r"\bor\s+\d+\s*=|\bselect\b|\bunion\b|\)\)\)|\|\*\||987-65-4329|bxss\.me)",
    re.IGNORECASE,
)
# Bot block was created in this window with random names + unconfirmed.
BOT_DATES = {"2026-06-20", "2026-06-21"}
RANDOM_NAME_RE = re.compile(r"^[a-z]{4,9}$")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def fix_mojibake(s: str) -> str:
    """Repair UTF-8 text that was mis-decoded (Ã/Â/Ù/à sequences, double-encoding)."""
    if not s:
        return ""
    if ftfy is not None:
        return ftfy.fix_text(s).strip()
    # fallback: single CP1252 -> UTF-8 round-trip
    if any(m in s for m in ("Ã", "Â", "Ù", "Ø", "Ð", "â", "à")):
        try:
            repaired = s.encode("cp1252", "ignore").decode("utf-8", "ignore")
            if repaired.strip():
                return repaired.strip()
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    return s.strip()


def normalize_country(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if len(raw) == 2 and raw.isalpha():
        return raw.upper()
    return NAME_TO_ISO.get(raw.lower(), "")


def parse_phone(raw: str, iso: str):
    """Return (e164, country_code, national_number, region) or (None,..) if invalid."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None, None, None, None

    region = iso if (iso and len(iso) == 2 and iso.isalpha()) else None
    cc = None
    if region:
        try:
            cc = phonenumbers.country_code_for_region(region)
        except Exception:  # noqa: BLE001
            cc = None

    candidates: list[str | tuple[str, str]] = []
    if cc:
        ccs = str(cc)
        if digits.startswith(ccs):
            nat = digits[len(ccs):]
            candidates.append("+" + ccs + nat)              # as-is intl
            candidates.append("+" + ccs + nat.lstrip("0"))  # drop trunk 0
        candidates.append(("NAT", digits))                  # treat as national
        candidates.append(("NAT", digits.lstrip("0")))
    candidates.append("+" + digits)                         # whole thing intl

    for cand in candidates:
        try:
            if isinstance(cand, tuple):
                num = phonenumbers.parse(cand[1], region)
            else:
                num = phonenumbers.parse(cand, None)
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(num):
            e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
            nat = phonenumbers.national_significant_number(num)
            reg = phonenumbers.region_code_for_number(num)
            return e164, str(num.country_code), nat, reg
    return None, None, None, None


def parse_time(raw: str) -> str:
    raw = (raw or "").strip()
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return ""


def classify(row, name_clean, e164, had_letters_in_phone):
    """Return a reason string if the row should be rejected, else ''."""
    raw_blob = f"{row.get('name','')} {row.get('mobile_number','')}"
    if INJECTION_RE.search(raw_blob):
        return "injection"
    if had_letters_in_phone:
        return "phone_has_letters"

    nm = name_clean.strip()
    if not nm or set(nm) <= {"?"}:
        return "empty_name"
    if EMAIL_RE.search(nm):
        return "email_as_name"
    if re.fullmatch(r"[\d\s+()\-.eE]{4,}", nm):  # digits / phone-ish / Excel sci-notation
        return "numeric_name"

    date = parse_time(row.get("subscribe_time", ""))[:10]
    confirmed = (row.get("number_confirmed", "") or "").strip().lower() == "yes"
    if date in BOT_DATES and not confirmed and RANDOM_NAME_RE.match(nm):
        return "bot_signup"

    if not e164:
        return "invalid_phone"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--encoding", default="utf-8",
                    help="input encoding (try 'utf-8' then 'cp1252' if garbled)")
    args = ap.parse_args()

    base, _ = os.path.splitext(args.input)
    out_clean = base + ".cleaned.csv"
    out_review = base + ".review.csv"

    stats = {"total": 0, "clean": 0, "duplicate": 0}
    reason_counts: dict[str, int] = {}
    rows_out = []

    with open(args.input, encoding=args.encoding, errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1
            name_clean = fix_mojibake(row.get("name", ""))
            iso = normalize_country(row.get("country", ""))
            raw_phone = row.get("mobile_number", "")
            had_letters = bool(re.search(r"[A-Za-z]", raw_phone))
            e164, cc, nat, reg = parse_phone(raw_phone, iso)
            # back-fill country from the number if it was blank/unknown
            if not iso and reg:
                iso = reg

            reason = classify(row, name_clean, e164, had_letters)
            confirmed = (row.get("number_confirmed", "") or "").strip().lower() == "yes"
            opted_out = (row.get("opt_out", "0") or "0").strip() == "1"
            channel = "sms" if iso == "US" else "whatsapp"

            rows_out.append({
                "id": row.get("id", "").strip(),
                "name": name_clean,
                "country": iso,
                "country_code": cc or "",
                "national_number": nat or "",
                "phone_e164": e164 or "",
                "channel": channel if e164 else "",
                "number_confirmed": "yes" if confirmed else "no",
                "opt_out": "1" if opted_out else "0",
                "active": "0" if (opted_out or not e164) else "1",
                "topics": (row.get("topics", "") or "").strip(),
                "reminder_types": (row.get("reminder_types", "") or "").strip(),
                "subscribe_time": parse_time(row.get("subscribe_time", "")),
                "_reason": reason,
            })

    # salvage: rows where ONLY the name was junk but the phone is valid ->
    # keep them (blank the bad name; the phone is what actually matters).
    salvage_reasons = {"empty_name", "numeric_name", "email_as_name"}
    for r in rows_out:
        if r["_reason"] in salvage_reasons and r["phone_e164"]:
            r["name"] = ""
            r["_reason"] = ""
            stats["salvaged"] = stats.get("salvaged", 0) + 1

    # dedupe valid rows by phone: prefer confirmed, then opted-in, then latest
    seen: dict[str, dict] = {}
    for r in rows_out:
        if r["_reason"] or not r["phone_e164"]:
            continue
        key = r["phone_e164"]
        prev = seen.get(key)
        if prev is None:
            seen[key] = r
        else:
            better = (
                (r["number_confirmed"] == "yes", r["active"] == "1", r["subscribe_time"])
                > (prev["number_confirmed"] == "yes", prev["active"] == "1", prev["subscribe_time"])
            )
            loser = prev if better else r
            loser["_reason"] = "duplicate"
            if better:
                seen[key] = r

    fields = ["id", "name", "country", "country_code", "national_number", "phone_e164",
              "channel", "number_confirmed", "opt_out", "active", "topics",
              "reminder_types", "subscribe_time"]

    # tell the user what to DO with each rejected row
    action_for = {
        "duplicate": "ignore - same number already in cleaned list",
        "invalid_phone": "discard - no usable phone number",
        "phone_has_letters": "discard - no usable phone number",
        "injection": "discard - spam/junk entry",
        "bot_signup": "re-opt-in required (unconfirmed bulk signup)",
        "empty_name": "discard - no name and no valid phone",
        "numeric_name": "discard - no name and no valid phone",
        "email_as_name": "discard - no valid phone",
    }
    action_counts: dict[str, int] = {}

    with open(out_clean, "w", encoding="utf-8", newline="") as fc, \
         open(out_review, "w", encoding="utf-8", newline="") as fr:
        wc = csv.DictWriter(fc, fieldnames=fields)
        wr = csv.DictWriter(fr, fieldnames=fields + ["reason", "action"])
        wc.writeheader()
        wr.writeheader()
        for r in rows_out:
            reason = r.pop("_reason")
            if reason:
                r["reason"] = reason
                r["action"] = action_for.get(reason, "review manually")
                wr.writerow(r)
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                action_counts[r["action"]] = action_counts.get(r["action"], 0) + 1
            else:
                wc.writerow(r)
                stats["clean"] += 1

    # report
    print(f"Rows read:        {stats['total']}")
    print(f"Recovered names:  {stats.get('salvaged', 0)} (blank/junk name, valid phone -> kept)")
    print(f"Clean & unique:   {stats['clean']}  -> {out_clean}")
    print(f"Sent to review:   {stats['total'] - stats['clean']}  -> {out_review}")
    print("  by reason:")
    for reason, n in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"    {reason:18} {n}")
    print("  what to do (action column):")
    for action, n in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"    {n:5}  {action}")


if __name__ == "__main__":
    main()
