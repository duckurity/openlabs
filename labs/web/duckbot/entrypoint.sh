#!/bin/sh
set -eu

case "${FLAG:-}" in
    REPLACE_ME_*)
        unset FLAG
        ;;
esac

if [ -z "${FLAG:-}" ] && [ ! -s /app/flag.txt ]; then
    FLAG="duck{$(python -c 'import secrets; print(secrets.token_hex(16))')}"
    export FLAG
fi

exec "$@"
