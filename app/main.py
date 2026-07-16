"""FastAPI entrypoint. Wires webhooks and initializes the DB.

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import api, schedule
from app.core.retry import retry_failed
from app.db import init_db
from app.webhooks import twilio

app = FastAPI(title="Stevie Broadcast Tool")

# Allow the static frontend (Vercel) to call this API from another origin.
# Set FRONTEND_ORIGIN to the Vercel URL in production; "*" is fine for testing.
_origins = os.environ.get("FRONTEND_ORIGIN", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.include_router(twilio.router)
app.include_router(schedule.router)
app.include_router(api.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/retry")
def admin_retry():
    """Manually trigger the failed-delivery retry sweep (hook up to cron later)."""
    return retry_failed()
