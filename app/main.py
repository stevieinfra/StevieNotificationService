"""FastAPI entrypoint. Wires webhooks and initializes the DB.

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI

from app import schedule
from app.core.retry import retry_failed
from app.db import init_db
from app.webhooks import twilio

app = FastAPI(title="Stevie Broadcast Tool")


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.include_router(twilio.router)
app.include_router(schedule.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/retry")
def admin_retry():
    """Manually trigger the failed-delivery retry sweep (hook up to cron later)."""
    return retry_failed()
