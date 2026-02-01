import json
import socket
import traceback
from confluent_kafka import Consumer

from configuration import NSP_SERVER, KAFKA_KEYSTORE_PASSWORD
from alarm_normalizer import normalize_alarm
from alarm_lifecycle import handle_alarm_lifecycle


def start_kafka_consumer(topic, stop_event, alarm_cache):
    conf = {
        "bootstrap.servers": f"{NSP_SERVER}:9193",

        # ✅ Use a stable consumer group
        "group.id": "nsp-alarm-consumer",

        # ✅ Manual offset control
        "enable.auto.commit": False,
        "auto.offset.reset": "latest",

        "security.protocol": "SSL",
        "ssl.keystore.location": "nsp_keystore.p12",
        "ssl.keystore.password": KAFKA_KEYSTORE_PASSWORD,
        "ssl.ca.location": "ca.pem",
    }

    consumer = Consumer(conf)
    consumer.subscribe([topic])

    print("📡 Kafka consumer started")
    print(f"📥 Subscribed to topic: {topic}")

    try:
        while not stop_event.is_set():
            try:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue

                if msg.error():
                    print("❌ Kafka error:", msg.error())
                    continue

                # ---------------------------
                # Decode message safely
                # ---------------------------
                try:
                    event = json.loads(msg.value().decode())
                except Exception as e:
                    print("❌ Invalid JSON from Kafka:", e)
                    continue

                # ---------------------------
                # Normalize alarm safely
                # ---------------------------
                try:
                    alarm = normalize_alarm(event, alarm_cache)
                except Exception:
                    print("❌ normalize_alarm() failed")
                    traceback.print_exc()
                    continue

                if not alarm:
                    continue

                # ---------------------------
                # Handle lifecycle SAFELY
                # ---------------------------
                try:
                    handle_alarm_lifecycle(alarm, alarm_cache)
                    # ✅ Commit offset only AFTER DB success
                    consumer.commit(msg, asynchronous=False)

                except Exception:
                    print("❌ handle_alarm_lifecycle() failed")
                    traceback.print_exc()
                    continue

                # ---------------------------
                # Log alarm (non-fatal)
                # ---------------------------
                print("\n🚨 REAL ALARM")
                print(json.dumps(alarm, indent=2, default=str))

            except Exception:
                # Absolute last-resort guard
                print("❌ Unexpected consumer loop error")
                traceback.print_exc()

    finally:
        consumer.close()
        print("🛑 Kafka consumer stopped")
