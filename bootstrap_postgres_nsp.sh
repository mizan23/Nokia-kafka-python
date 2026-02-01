#!/usr/bin/env bash
set -euo pipefail

### ===============================
### CONFIG
### ===============================
PG_DB="nsp"
PG_USER="nsp_user"
PG_PASS="nsp_pass"

log() {
  echo -e "\n🔹 $1"
}

### ===============================
### Step 1: Install PostgreSQL
### ===============================
if ! command -v psql >/dev/null 2>&1; then
  log "PostgreSQL not found. Installing..."
  sudo apt update
  sudo apt install -y postgresql postgresql-contrib
else
  log "PostgreSQL already installed"
fi

### ===============================
### Step 2: Start service
### ===============================
log "Ensuring PostgreSQL service is running"
sudo systemctl enable postgresql
sudo systemctl start postgresql

### ===============================
### Step 3: Create database
### ===============================
log "Creating database if not exists"

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE DATABASE ${PG_DB};"
  log "Database '${PG_DB}' created"
else
  log "Database '${PG_DB}' already exists"
fi

### ===============================
### Step 4: Create user
### ===============================
log "Creating user if not exists"

sudo -u postgres psql <<EOF
DO \$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_roles WHERE rolname = '${PG_USER}'
   ) THEN
      CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';
   END IF;
END
\$\$;
EOF

### ===============================
### Step 5: Schema + tables
### ===============================
log "Creating alarm tables"

sudo -u postgres psql -d "${PG_DB}" <<'EOF'

-- ===============================
-- Active alarms
-- ===============================
CREATE TABLE IF NOT EXISTS active_alarms (
    alarm_id TEXT PRIMARY KEY,
    alarm JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_updated TIMESTAMPTZ DEFAULT now()
);

-- ===============================
-- Alarm history
-- ===============================
CREATE TABLE IF NOT EXISTS alarm_history (
    alarm_id TEXT NOT NULL,
    alarm JSONB NOT NULL,
    cleared_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (alarm_id, cleared_at)
);

-- ===============================
-- last_updated trigger
-- ===============================
CREATE OR REPLACE FUNCTION set_last_updated()
RETURNS trigger AS $$
BEGIN
  NEW.last_updated = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_active_alarms_updated ON active_alarms;

CREATE TRIGGER trg_active_alarms_updated
BEFORE UPDATE ON active_alarms
FOR EACH ROW
EXECUTE FUNCTION set_last_updated();

-- ===============================
-- Indexes (JSON-friendly)
-- ===============================
CREATE INDEX IF NOT EXISTS idx_active_alarms_alarm_gin
ON active_alarms USING GIN (alarm);

CREATE INDEX IF NOT EXISTS idx_alarm_history_alarm_gin
ON alarm_history USING GIN (alarm);

EOF

### ===============================
### Step 6: Permissions
### ===============================
log "Granting privileges to application user"

sudo -u postgres psql -d "${PG_DB}" <<EOF
-- Database access
GRANT CONNECT ON DATABASE ${PG_DB} TO ${PG_USER};

-- Schema access
GRANT USAGE, CREATE ON SCHEMA public TO ${PG_USER};

-- Table privileges
GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO ${PG_USER};

-- Sequence privileges (future-proof)
GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO ${PG_USER};

-- Default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${PG_USER};

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO ${PG_USER};
EOF

log "✅ PostgreSQL alarm schema ready"

### ===============================
### Step 2.5: Fix local authentication
### ===============================
log "Configuring PostgreSQL authentication (md5)"

sudo bash -c '
PG_HBA=$(sudo -u postgres psql -tAc "SHOW hba_file;")

if ! grep -q "^local\s\+all\s\+all\s\+md5" "$PG_HBA"; then
  sed -i.bak \
    -e "s/^local\s\+all\s\+all\s\+peer/local all all md5/" \
    "$PG_HBA"
  echo "🔹 Updated pg_hba.conf (peer → md5)"
else
  echo "🔹 pg_hba.conf already uses md5"
fi
'

log "Reloading PostgreSQL"
sudo systemctl reload postgresql
