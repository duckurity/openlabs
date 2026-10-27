#!/bin/sh
set -eu

python -B -c 'from app.state import main; raise SystemExit(main())' --initialize
exec gunicorn --config /opt/sealdesk/gunicorn.conf.py 'app:create_app()'
