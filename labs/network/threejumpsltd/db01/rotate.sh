#!/bin/bash
set -eu
printf 'Database maintenance started at %s\n' "$(date -Is)"
find /var/backups/db -type f -name '*.sql.gz' -mtime +14 -delete
printf 'Database maintenance completed.\n'
