# NSP Kafka Alarm Consumer (Python)

A production-ready **Python Kafka consumer** for **Nokia NSP / NFMT alarm notifications**.

This project:
- Subscribes to NSP alarm notifications
- Consumes alarms from Kafka over SSL
- Normalizes and filters noisy alarms
- Stores active alarms and alarm history in PostgreSQL
- Automatically handles alarm lifecycle (create / clear)
- Runs safely as a systemd service
- Cleans up historical alarms with a systemd timer

---

## 📌 Features

- Kafka SSL consumer (`confluent-kafka`)
- Token-based authentication with auto-refresh
- Robust alarm filtering policy
- PostgreSQL-backed alarm lifecycle
- Safe shutdown & cleanup (subscription + token revoke)
- systemd service for 24/7 operation
- systemd timer for history cleanup

---

## 📂 Project Structure

```
kafka-python/
├── alarm_filters.py
├── alarm_normalizer.py
├── alarm_lifecycle.py
├── kafka_consumer.py
├── full_flow_main.py
├── token_manager_automatic_refresh.py
├── create_kafka_subscription.py
├── renew_subscription.py
├── delete_subscription.py
├── revoke_token.py
├── cleanup_history.py
├── alarm_viewer.py
├── configuration.py
├── bootstrap_postgres_nsp.sh
├── requirements.txt
├── .env.example
└── venv/
```

---

## 🚀 How It Works

1. Authenticates to NSP using REST API
2. Creates a Kafka subscription for alarm notifications
3. Consumes alarm events over SSL
4. Normalizes NSP alarm payloads
5. Filters noisy / non-actionable alarms
6. Writes active alarms to PostgreSQL
7. Moves cleared alarms to history
8. Runs continuously as a systemd service

---

## 🔧 Requirements

- Python 3.9+
- Linux server (Ubuntu recommended)
- PostgreSQL 13+
- Kafka access from NSP

---

## 📦 Installation

```bash
git clone https://github.com/mizan23/kafka-python.git
cd kafka-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file (see `.env.example`):

```
NSP_SERVER=192.168.42.7
NSP_USERNAME=your_username
NSP_PASSWORD=your_password
KAFKA_KEYSTORE_PASSWORD=your_keystore_password
```

Certificates and keystores are intentionally excluded from Git.

---

## 🗄️ PostgreSQL Setup

```bash
chmod +x bootstrap_postgres_nsp.sh
./bootstrap_postgres_nsp.sh
```

---

## ▶️ Run Manually

```bash
python full_flow_main.py
```

---

## 🛠️ Run as systemd Service

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nsp-kafka-consumer
```

Check status:

```bash
systemctl status nsp-kafka-consumer
```

---

## 🧹 Alarm History Cleanup

Cleanup runs via systemd timer.

```bash
systemctl list-timers | grep nsp
```

---

## 📊 Alarm Viewer

```bash
python alarm_viewer.py active
python alarm_viewer.py history
python alarm_viewer.py active-full <alarm_id>
```

---

## 🔒 Security Notes

- Do not commit certificates or keystores
- Rotate credentials if repository was public

---

## 🧑‍💻 Author

Mizanur Rahman

---

## 📄 License

Internal / Private use
