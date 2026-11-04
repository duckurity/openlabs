#!/bin/sh
set -e

# Start verdaccio in background
verdaccio --config /verdaccio/conf/config.yaml &
VERDACCIO_PID=$!

# Wait for verdaccio to be ready (retry up to 60s)
echo "[seed] waiting for verdaccio..."
for i in $(seq 1 60); do
  if wget -q --spider http://127.0.0.1:4873/-/ping 2>/dev/null; then
    echo "[seed] verdaccio is ready"
    break
  fi
  sleep 1
done

# Final check
if ! wget -q --spider http://127.0.0.1:4873/-/ping 2>/dev/null; then
  echo "[seed] ERROR: verdaccio did not start"
  exit 1
fi

# Publish seed package
if [ -d /seed/shopx-utils ]; then
  echo "[seed] publishing legacy shopx-utils@1.4.2..."
  cd /seed/shopx-utils
  npm publish \
    --registry http://127.0.0.1:4873/ \
    --//127.0.0.1:4873/:_authToken="seed-token" \
    2>&1 || echo "[seed] already published (or publish conflict) - continuing"
fi

# Wait for verdaccio to exit
wait $VERDACCIO_PID
