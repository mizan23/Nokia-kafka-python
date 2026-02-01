import threading
import signal
import sys
import atexit
import requests

from alarm_cache import AlarmCache
from alarm_lifecycle import get_active_power_issues, get_active_los_alarms
from configuration import AUTH_URL, REVOKE_URL, USERNAME, PASSWORD
from token_manager import TokenManager
from create_kafka_subscription import create_subscription
from renew_subscription import renew_subscription
from delete_subscription import delete_subscription
from kafka_consumer import start_kafka_consumer


# -------------------------------
# Global state
# -------------------------------

stop_event = threading.Event()
subscription_id = None
token_mgr = None
cleanup_done = False


# -------------------------------
# Cleanup logic (SAFE + IDPOTENT)
# -------------------------------
def cleanup():
    global cleanup_done
    if cleanup_done:
        return
    cleanup_done = True

    print("\n🧹 Cleaning up NSP resources...")
    stop_event.set()

    if subscription_id:
        try:
            delete_subscription(token_mgr, subscription_id)
        except Exception as e:
            print("⚠️ Failed to delete subscription:", e)

    if token_mgr:
        try:
            token_mgr.revoke()
        except Exception as e:
            print("⚠️ Failed to revoke token:", e)

# -------------------------------
# Signal handlers
# -------------------------------

def shutdown_handler(sig, frame):
    print("\n🛑 Shutdown signal received")
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# ✅ Run cleanup even on unhandled exception
atexit.register(cleanup)


# -------------------------------
# Auto-renew thread
# -------------------------------

def auto_renew_subscription(token_mgr, subscription_id, stop_event, interval=1800):
    while True:

        # ⏸ Wait for interval OR shutdown
        if stop_event.wait(interval):
            # 🛑 Shutdown requested
            return

        # 🛑 Double-check before API call
        if stop_event.is_set():
            return

        try:
            renew_subscription(token_mgr, subscription_id)

            # 🛑 Don't log during shutdown
            if not stop_event.is_set():
                print("🔁 Subscription renewed")

        except requests.HTTPError as e:
            if stop_event.is_set():
                return

            if e.response and e.response.status_code == 401:
                print("🔐 Token expired during renewal, re-authenticating")
                token_mgr.ensure_token()
            else:
                print("❌ Subscription renewal failed:", e)

        except Exception as e:
            if stop_event.is_set():
                return
            print("❌ Unexpected renewal error:", e)

# -------------------------------
# Main
# -------------------------------

if __name__ == "__main__":

    try:
        token_mgr = TokenManager(
        auth_url=AUTH_URL,
        revoke_url=REVOKE_URL,
        client_id=USERNAME,
        client_secret=PASSWORD,
        token_file="/home/mizan/kafka-python/token.json",
        verify_ssl=False,
    )

        subscription_id, topic_id = create_subscription(token_mgr)

        threading.Thread(
            target=auto_renew_subscription,
            args=(token_mgr, subscription_id, stop_event),
            daemon=True,
            name="subscription-renew-thread"
        ).start()

        alarm_cache = AlarmCache()

        # Load from DB ONCE
        alarm_cache.load_power_issues(get_active_power_issues())
        alarm_cache.load_los_alarms(get_active_los_alarms())

        start_kafka_consumer(topic_id, stop_event, alarm_cache)

    except Exception as e:
        print("❌ Fatal error:", e)
        cleanup()
        sys.exit(1)
