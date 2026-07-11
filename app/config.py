"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_sms_from: str = ""
    twilio_whatsapp_from: str = "+14155238886"  # Twilio WhatsApp sandbox default
    twilio_whatsapp_template_sid: str = ""

    # App
    public_base_url: str = "http://localhost:8000"
    cloudcannon_webhook_secret: str = "change-me"
    dry_run: bool = True
    database_path: str = "data/stevie.db"

    # Quiet hours in the recipient's local time (24h). Sends outside are deferred.
    quiet_hours_start: int = 9
    quiet_hours_end: int = 21


settings = Settings()
