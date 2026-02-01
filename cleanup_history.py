import psycopg2
from datetime import timedelta, datetime

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "nsp",
    "user": "nsp_user",
    "password": "nsp_pass",
}

RETENTION_DAYS = 90


def cleanup():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM alarm_history
                WHERE cleared_at < now() - interval '%s days'
                """,
                (RETENTION_DAYS,)
            )

            deleted = cur.rowcount
            conn.commit()

            print(f"🧹 Deleted {deleted} historical alarms older than {RETENTION_DAYS} days")
    finally:
        conn.close()


if __name__ == "__main__":
    cleanup()
