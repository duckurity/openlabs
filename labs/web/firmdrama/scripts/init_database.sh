#!/bin/sh
set -eu

BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MYSQL_SOCKET=${FIRMDRAMA_MYSQL_SOCKET:-/run/mysqld/firmdrama-mysql.sock}
MYSQL_DATA_DIR=${FIRMDRAMA_MYSQL_DATA_DIR:-/var/lib/mysql}
MYSQL_PASSWORD=${FIRMDRAMA_DB_PASSWORD:-firmdrama-local-only}

mkdir -p "$(dirname "$MYSQL_SOCKET")" "$MYSQL_DATA_DIR" /var/log/mysql

if [ ! -d "$MYSQL_DATA_DIR/mysql" ]; then
    mysqld --initialize-insecure --mysqlx=OFF --user=firmdrama --datadir="$MYSQL_DATA_DIR"
fi

MYSQL_PID_FILE=${FIRMDRAMA_MYSQL_PID_FILE:-/run/mysqld/firmdrama-mysql.pid}
mysqld --user=firmdrama --datadir="$MYSQL_DATA_DIR" --socket="$MYSQL_SOCKET" --pid-file="$MYSQL_PID_FILE" --bind-address=127.0.0.1 --mysqlx=OFF &
MYSQL_PID=$!

cleanup() {
    if kill -0 "$MYSQL_PID" 2>/dev/null; then
        kill "$MYSQL_PID" 2>/dev/null || true
        wait "$MYSQL_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

i=0
until mysqladmin --protocol=socket --socket="$MYSQL_SOCKET" -uroot ping --silent >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "MySQL did not become ready" >&2
        exit 1
    fi
    sleep 1
done

export FIRMDRAMA_DB_PASSWORD="$MYSQL_PASSWORD"
export FIRMDRAMA_MYSQL_SOCKET="$MYSQL_SOCKET"
PYTHONPATH="$BASE_DIR" python3 "$BASE_DIR/scripts/configure_database.py"
mysql --protocol=socket --socket="$MYSQL_SOCKET" -uroot < "$BASE_DIR/database/schema.sql"
mysql --protocol=socket --socket="$MYSQL_SOCKET" -uroot < "$BASE_DIR/database/seed.sql"

export FIRMDRAMA_DB_HOST=127.0.0.1
export FIRMDRAMA_DB_PORT=3306
export FIRMDRAMA_DB_NAME=firmdrama
export FIRMDRAMA_DB_USER=firmdrama
export FIRMDRAMA_DB_PASSWORD="$MYSQL_PASSWORD"
export FIRMDRAMA_MYSQL_SOCKET="$MYSQL_SOCKET"
PYTHONPATH="$BASE_DIR" python3 "$BASE_DIR/scripts/generate_flags.py"

trap - EXIT INT TERM
echo "firmdrama database initialized"
