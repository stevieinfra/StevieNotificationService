"""Phone validation + country derivation via libphonenumber.

We STORE country explicitly on the subscriber. This module is a validator and a
*fallback* deriver only. Critically, +1 maps to both US and CA, so we never let
the dial code decide routing on its own.
"""
from __future__ import annotations

from dataclasses import dataclass

import phonenumbers


@dataclass
class PhoneCheck:
    ok: bool
    e164: str | None
    region: str | None   # ISO region libphonenumber *guesses* (e.g. 'US', 'CA', 'IN')
    reason: str | None = None


def validate(phone: str) -> PhoneCheck:
    """Validate an E.164-ish string; return normalized E.164 + guessed region."""
    try:
        parsed = phonenumbers.parse(phone, None)  # None => must include country code
    except phonenumbers.NumberParseException as exc:
        return PhoneCheck(ok=False, e164=None, region=None, reason=str(exc))

    if not phonenumbers.is_valid_number(parsed):
        return PhoneCheck(ok=False, e164=None, region=None, reason="not a valid number")

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    region = phonenumbers.region_code_for_number(parsed)
    return PhoneCheck(ok=True, e164=e164, region=region)
