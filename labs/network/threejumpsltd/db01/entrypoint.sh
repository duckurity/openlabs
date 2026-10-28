#!/bin/bash
set -euo pipefail
install -d -m 0755 /run/sshd
ssh-keygen -A

# The database is initialized at container start so recreating the container
# returns it to a clean challenge state. No database volume is mounted.
service postgresql start
PG_VERSION="$(ls /etc/postgresql | sort -V | tail -n1)"

if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='inventory_app'" | grep -q '^1$'; then
  runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE ROLE inventory_app LOGIN PASSWORD 'Inv3ntory_Read_2026!'"
fi
if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='inventory'" | grep -q '^1$'; then
  runuser -u postgres -- createdb -O inventory_app inventory
fi
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -d inventory <<'SQL'
CREATE TABLE IF NOT EXISTS assets (
  id integer PRIMARY KEY,
  asset_name text NOT NULL,
  status text NOT NULL
);
INSERT INTO assets (id, asset_name, status) VALUES
  (1, 'inventory-api', 'active'),
  (2, 'legacy-export-worker', 'retired'),
  (3, 'backup-rotation', 'maintenance')
ON CONFLICT (id) DO NOTHING;
GRANT CONNECT ON DATABASE inventory TO inventory_app;
GRANT USAGE ON SCHEMA public TO inventory_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO inventory_app;
SQL
service postgresql reload
exec /usr/sbin/sshd -D -e
