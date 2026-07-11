"""Simulate a CloudCannon publish webhook against the running app.

Usage:
  python -m scripts.simulate_publish
  python -m scripts.simulate_publish --duplicate   # fire twice to prove dedupe

Requires the app running:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import sys

import httpx

from app.config import settings

URL = f"{settings.public_base_url.rstrip('/')}/webhooks/cloudcannon"

PAYLOAD = {
    "type": "broadcast",                 # only this type triggers a send
    "id": "stevie-2026-winners-announced",  # stable id => deterministic dedupe
    "title": "2026 Stevie Awards Winners Announced!",
    "body": "The results are in. See who took home Gold, Silver, and Bronze this year.",
    "link": "https://stevieawards.com/winners/2026",
    "audience": "all",                   # or a country code like 'US'
}


def main() -> None:
    headers = {"X-CC-Secret": settings.cloudcannon_webhook_secret}
    with httpx.Client(timeout=30) as client:
        r = client.post(URL, json=PAYLOAD, headers=headers)
        print(f"POST {URL} -> {r.status_code}")
        print(r.json())

        if "--duplicate" in sys.argv:
            r2 = client.post(URL, json=PAYLOAD, headers=headers)
            print(f"\n[duplicate] -> {r2.status_code}")
            print(r2.json())


if __name__ == "__main__":
    main()
