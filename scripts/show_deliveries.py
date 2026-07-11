"""Print a breakdown of the deliveries table. Usage: python -m scripts.show_deliveries"""
from app.db import get_conn


def main() -> None:
    with get_conn() as c:
        print("--- by channel + status ---")
        for r in c.execute(
            "SELECT channel, status, COUNT(*) n FROM deliveries "
            "GROUP BY channel, status ORDER BY channel, status"
        ):
            print(f"  {r['channel']:9} {r['status']:9} {r['n']}")

        print("--- skipped (with reason) ---")
        for r in c.execute(
            "SELECT s.name, d.channel, d.reason FROM deliveries d "
            "JOIN subscribers s ON s.id=d.subscriber_id WHERE d.status='skipped'"
        ):
            print(f"  {r['name']:14} {r['channel']:9} {r['reason']}")

        print("--- sample sent rows (message_sid) ---")
        for r in c.execute(
            "SELECT s.name, s.country, d.channel, d.status, d.message_sid FROM deliveries d "
            "JOIN subscribers s ON s.id=d.subscriber_id WHERE d.status='queued' LIMIT 8"
        ):
            print(f"  {r['name']:14} {r['country']:3} {r['channel']:9} {r['status']:7} {r['message_sid']}")


if __name__ == "__main__":
    main()
