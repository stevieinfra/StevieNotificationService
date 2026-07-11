"""End-to-end dedupe + routing test over the broadcaster, in DRY_RUN."""
from datetime import datetime, timezone

from app.core.broadcaster import run_broadcast
from app.db import get_conn, init_db


def _seed():
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM deliveries")
        conn.execute("DELETE FROM broadcasts")
        conn.execute("DELETE FROM subscribers")
        conn.executemany(
            """INSERT INTO subscribers
               (phone, country, name, sms_opt_in, whatsapp_opt_in, language, timezone, active)
               VALUES (?, ?, ?, ?, ?, 'en', 'UTC', 1)""",
            [
                ("+12025550101", "US", "US-optin", 1, 0),      # -> SMS
                ("+12025550102", "US", "US-no-optin", 0, 0),   # -> skipped
                ("+919812345303", "IN", "IN-optin", 0, 1),     # -> WhatsApp
                ("+14165550201", "CA", "CA-optin", 0, 1),      # -> WhatsApp (not SMS!)
            ],
        )
        conn.execute(
            "INSERT INTO broadcasts (id, title, body, link, audience, created_at) "
            "VALUES ('b1', 'T', 'B', NULL, 'all', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )


def test_routing_and_skip_counts():
    _seed()
    summary = run_broadcast("b1")
    assert summary["sent"] == 3        # US-optin + IN + CA
    assert summary["skipped"] == 1     # US-no-optin


def test_rerun_never_double_sends():
    _seed()
    run_broadcast("b1")
    second = run_broadcast("b1")
    # Everything already claimed -> all duplicates, zero new sends.
    assert second["sent"] == 0
    assert second["duplicate"] == 3

    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM deliveries").fetchone()["c"]
    assert n == 4  # 3 sent + 1 skipped, one row per subscriber, no dupes
