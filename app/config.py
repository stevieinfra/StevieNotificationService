"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Twilio (SMS). WhatsApp is handled separately via the Meta Cloud API (Node).
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_sms_from: str = ""

    # App
    public_base_url: str = "http://localhost:8000"
    dry_run: bool = True
    database_path: str = "data/stevie.db"

    # Cleaned subscriber list the schedule form targets (prototype source of truth).
    subscribers_csv: str = "data/SMS subscribers export 7-8-26.cleaned.csv"

    # Quiet hours in the recipient's local time (24h). Sends outside are deferred.
    quiet_hours_start: int = 9
    quiet_hours_end: int = 21


settings = Settings()
