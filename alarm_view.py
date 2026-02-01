#!/usr/bin/env python3
import psycopg2
import json
from tabulate import tabulate
from argparse import ArgumentParser

# -------------------------------
# Database configuration
# -------------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "nsp",
    "user": "nsp_user",
    "password": "nsp_pass",
}

# -------------------------------
# DB helper
# -------------------------------
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# -------------------------------
# SQL filter builder
# -------------------------------
def build_filters(severity, ne, from_time, to_time, time_field, correlated_only=False, include_root=True):
    clauses = []
    params = []

    if severity:
        clauses.append("alarm->>'severity' = %s")
        params.append(severity)

    if ne:
        clauses.append("alarm->>'ne_name' ILIKE %s")
        params.append(f"%{ne}%")

    if from_time:
        clauses.append(f"{time_field} >= %s")
        params.append(from_time)

    if to_time:
        clauses.append(f"{time_field} <= %s")
        params.append(to_time)

    if correlated_only:
        clauses.append("alarm->>'alarm_name' IN ('Power Adjustment Required', 'Transport Failure', 'OPS Protection Loss of Redundancy')")
    elif not include_root:
        clauses.append("alarm->>'alarm_name' NOT IN ('Power Issue', 'Loss of signal - OCH')")

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    return where_sql, params

# -------------------------------
# ACTIVE alarms (list)
# -------------------------------
def show_active(limit, severity, ne, from_time, to_time, correlated_only, include_root):
    where_sql, params = build_filters(
        severity, ne, from_time, to_time, "alarm->>'last_detected'", correlated_only, include_root
    )

    sql = f"""
    SELECT
        alarm_id,
        alarm->>'alarm_name' AS alarm_name,
        alarm->>'ne_name' AS ne_name,
        alarm->>'severity' AS severity,
        alarm->>'first_detected' AS first_detected,
        alarm->>'last_detected' AS last_detected,
        last_updated
    FROM active_alarms
    {where_sql}
    ORDER BY last_updated DESC
    LIMIT %s;
    """
    params.append(limit)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        print("✅ No active alarms")
        return

    print("\n🚨 ACTIVE ALARMS\n")
    print(tabulate(
        rows,
        headers=[
            "Alarm ID",
            "Alarm Name",
            "NE",
            "Severity",
            "First Detected",
            "Last Detected",
            "Updated At"
        ],
        tablefmt="psql"
    ))

# -------------------------------
# HISTORY alarms (list)
# -------------------------------
def show_history(limit, severity, ne, from_time, to_time):
    where_sql, params = build_filters(
        severity, ne, from_time, to_time, "cleared_at"
    )

    sql = f"""
    SELECT
        alarm_id,
        alarm->>'alarm_name' AS alarm_name,
        alarm->>'ne_name' AS ne_name,
        alarm->>'severity' AS severity,
        alarm->>'last_detected' AS last_detected,
        cleared_at
    FROM alarm_history
    {where_sql}
    ORDER BY cleared_at DESC
    LIMIT %s;
    """

    params.append(limit)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        print("✅ No historical alarms")
        return

    print("\n📜 ALARM HISTORY\n")
    print(tabulate(
        rows,
        headers=[
            "Alarm ID",
            "Alarm Name",
            "NE",
            "Severity",
            "Last Detected",
            "Cleared At"
        ],
        tablefmt="psql"
    ))

# -------------------------------
# FULL views
# -------------------------------
def show_active_full(alarm_id):
    sql = "SELECT alarm FROM active_alarms WHERE alarm_id = %s;"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (alarm_id,))
        row = cur.fetchone()
    if not row:
        print("❌ Active alarm not found")
        return
    print("\n🚨 FULL ACTIVE ALARM\n")
    print(json.dumps(row[0], indent=2, default=str))

def show_history_full(alarm_id):
    sql = """
    SELECT alarm, cleared_at
    FROM alarm_history
    WHERE alarm_id = %s
    ORDER BY cleared_at DESC
    LIMIT 1;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (alarm_id,))
        row = cur.fetchone()
    if not row:
        print("❌ History alarm not found")
        return
    alarm, cleared_at = row
    alarm["cleared_at"] = str(cleared_at)
    print("\n📜 FULL HISTORICAL ALARM\n")
    print(json.dumps(alarm, indent=2, default=str))

# -------------------------------
# Delete ACTIVE / HISTORY
# -------------------------------
def delete_active(alarm_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM active_alarms WHERE alarm_id = %s;", (alarm_id,))
        conn.commit()
        print("🗑️ Deleted ACTIVE alarm" if cur.rowcount else "❌ Not found")

def delete_history(alarm_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM alarm_history WHERE alarm_id = %s;", (alarm_id,))
        conn.commit()
        print("🗑️ Deleted HISTORY alarm(s)" if cur.rowcount else "❌ Not found")

# -------------------------------
# PURGE helpers
# -------------------------------
def purge_history():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM alarm_history;")
        conn.commit()
        print(f"🧹 Purged {cur.rowcount} historical alarms")

def purge_active():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM active_alarms;")
        conn.commit()
        print(f"🧹 Purged {cur.rowcount} active alarms")

# -------------------------------
# CLI
# -------------------------------
def add_common_filters(p):
    p.add_argument("--limit", type=int, choices=[20, 30, 40, 50, 100], default=20)
    p.add_argument("--severity", choices=["CRITICAL", "MAJOR", "MINOR", "WARNING", "INFO", "CLEAR"])
    p.add_argument("--ne", help="Filter by NE name (partial match)")
    p.add_argument("--from-time", help="Start time (ISO 8601, e.g. 2026-01-23T10:00:00Z)")
    p.add_argument("--to-time", help="End time (ISO 8601, e.g. 2026-01-23T12:00:00Z)")

def main():
    parser = ArgumentParser("NSP Alarm Viewer")
    sub = parser.add_subparsers(dest="cmd")

    # Active
    p = sub.add_parser("active", help="Show active alarms")
    add_common_filters(p)
    p.add_argument("--correlated-only", action="store_true", help="Show only correlated (child) alarms")
    p.add_argument("--exclude-root", action="store_true", help="Hide root alarms (Power Issue / LOS-OCH)")

    # History
    p = sub.add_parser("history", help="Show alarm history")
    add_common_filters(p)

    # Full views
    sub.add_parser("active-full", help="Show full active alarm JSON").add_argument("alarm_id")
    sub.add_parser("history-full", help="Show full historical alarm JSON").add_argument("alarm_id")

    # Delete
    sub.add_parser("delete-active", help="Delete active alarm").add_argument("alarm_id")
    sub.add_parser("delete-history", help="Delete history alarm").add_argument("alarm_id")

    # Purge
    sub.add_parser("purge-history", help="Delete ALL history alarms")
    sub.add_parser("purge-active", help="Delete ALL active alarms")

    args = parser.parse_args()

    if args.cmd == "active":
        show_active(args.limit, args.severity, args.ne, args.from_time, args.to_time, args.correlated_only, not args.exclude_root)
    elif args.cmd == "history":
        show_history(args.limit, args.severity, args.ne, args.from_time, args.to_time)
    elif args.cmd == "active-full":
        show_active_full(args.alarm_id)
    elif args.cmd == "history-full":
        show_history_full(args.alarm_id)
    elif args.cmd == "delete-active":
        delete_active(args.alarm_id)
    elif args.cmd == "delete-history":
        delete_history(args.alarm_id)
    elif args.cmd == "purge-history":
        purge_history()
    elif args.cmd == "purge-active":
        purge_active()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
