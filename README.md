# NSP Kafka Alarm Consumer

A **production‑ready Kafka consumer and alarm correlation pipeline** for **Nokia NSP / NFM‑T**.

This project consumes NSP fault notifications from Kafka, normalizes and correlates alarms in‑memory, persists alarm lifecycle state in PostgreSQL, and exposes a clean CLI for operators.

Designed for **24×7 carrier‑grade operation** with:
- zero message loss
- idempotent DB writes
- safe shutdown & cleanup
- correlation without DB calls in the hot path

---

## ✨ Features

- 🔐 Secure OAuth token lifecycle (auto refresh + revoke)
- 📡 Kafka SSL consumer (manual offset commit)
- 🧠 In‑memory correlation cache (Power / LOS‑OCH)
- 🧹 Intelligent alarm suppression (root/child logic)
- 🗄 PostgreSQL active + history storage
- ♻️ Retention cleanup
- 🛠 Operator CLI for alarms
- 🚀 systemd‑ready service

---

## 🧱 Architecture Overview

```
NSP → Kafka → Consumer → Normalize → Correlate → DB
                         ↓
                     Drop Noise
```

**Hot path is DB‑free** — correlation uses only in‑memory cache.

---

## 📂 Project Structure

```
.
├── full_flow_main.py          # Main entry point
├── kafka_consumer.py          # Kafka SSL consumer
├── alarm_normalizer.py        # Normalize NSP payloads
├── alarm_filters.py           # Correlation + suppression rules
├── alarm_cache.py             # In‑memory correlation cache
├── alarm_lifecycle.py         # DB + cache lifecycle handler
├── alarm_view.py              # CLI for active/history alarms
├── object_parser.py           # Affected object parser
├── severity_mapper.py         # NSP → normalized severity
├── token_manager.py           # OAuth token lifecycle
├── create_kafka_subscription.py
├── renew_subscription.py
├── delete_subscription.py
├── configuration.py           # Environment config
├── cleanup_history.py         # Retention cleanup
├── bootstrap_postgres_nsp.sh  # PostgreSQL bootstrap script
├── requirements.txt
└── README.md
```

---

## 🛠 Requirements

- Python **3.9+**
- PostgreSQL **13+**
- Kafka access from NSP
- OpenSSL libraries

Python packages:
```
confluent-kafka
psycopg2-binary
requests
python-dotenv
pytz
tabulate
```

---

## 🔧 Installation

### 1️⃣ Clone repository

```bash
git clone https://github.com/your-org/nsp-kafka-alarm-consumer.git
cd nsp-kafka-alarm-consumer
```

### 2️⃣ Create virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🗄 PostgreSQL Setup

Run **once**:

```bash
chmod +x bootstrap_postgres_nsp.sh
./bootstrap_postgres_nsp.sh
```

Creates:
- `active_alarms`
- `alarm_history`
- JSONB indexes
- triggers

---

## 🔐 Environment Configuration

Create `.env` file:

```env
NSP_SERVER=192.168.42.7
NSP_USERNAME=client_id
NSP_PASSWORD=client_secret
KAFKA_KEYSTORE_PASSWORD=change_me
```

---

## ▶️ Running Manually

```bash
source venv/bin/activate
python full_flow_main.py
```

What happens:
1. OAuth token acquired
2. Kafka subscription created
3. Cache preloaded from DB
4. Kafka consumer starts
5. Alarms normalized → correlated → stored

---

## ⚙️ Running as systemd Service (Recommended)

### Create log directory

```bash
sudo mkdir -p /var/log/nsp
sudo chown $USER:$USER /var/log/nsp
```

### Create service file

```bash
sudo nano /etc/systemd/system/nsp-kafka-consumer.service
```

Paste:

```ini
[Unit]
Description=NSP Kafka Alarm Consumer
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=mizan
Group=mizan
WorkingDirectory=/home/mizan/kafka-python
ExecStart=/home/mizan/kafka-python/venv/bin/python full_flow_main.py
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10
StandardOutput=append:/var/log/nsp/nsp-consumer.log
StandardError=append:/var/log/nsp/nsp-consumer.err
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Enable & start

```bash
sudo systemctl daemon-reload
sudo systemctl enable nsp-kafka-consumer
sudo systemctl start nsp-kafka-consumer
```

### Logs

```bash
tail -f /var/log/nsp/nsp-consumer.log
tail -f /var/log/nsp/nsp-consumer.err
```

---

## 🧠 Alarm Correlation Logic

### Power Correlation

- **Root**: `Power Issue` (PHYSICALCONNECTION)
- **Children**:
  - Power Adjustment Required
  - Power Adjustment Failure
- **Window**: ±10 minutes
- **Match**: OPS shelf span

### LOS‑OCH Correlation

- **Root**: Loss of signal – OCH (CRITICAL)
- **Children**:
  - Transport Failure
  - OPS Protection Loss of Redundancy
- **Window**: ±30 seconds
- **Match priority**:
  1. OPS span
  2. Same NE

Children are **suppressed**, roots always pass.

---

## 🧪 Alarm Viewer CLI

### Active alarms

```bash
python alarm_view.py active --limit 30
```

### Correlated only

```bash
python alarm_view.py active --correlated-only
```

### History

```bash
python alarm_view.py history --severity CRITICAL
```

### Full alarm JSON

```bash
python alarm_view.py active-full <alarm_id>
```

---

## 🧹 Retention Cleanup

```bash
python cleanup_history.py
```

Deletes alarms older than **90 days**.

---

## 🛑 Safe Shutdown Guarantees

On SIGTERM / SIGINT:

- Kafka consumer stops
- Subscription deleted
- Token revoked
- Offsets committed only after DB success

No duplicates. No leaks.

---

## 🚀 Production Notes

- Consumer group is **stable**
- Manual commits guarantee **exact‑once DB writes**
- Correlation cache prevents DB amplification
- JSONB indexes keep queries fast

---

## 📜 License

MIT License

---

## 🤝 Contributing

PRs welcome. Keep hot‑path logic **DB‑free**.

---

## 🧠 Author

Built for real‑world NSP deployments — not demos.

