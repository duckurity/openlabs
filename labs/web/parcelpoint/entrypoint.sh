#!/bin/sh
set -eu
umask 077
python -m app.seed
exec gunicorn --config gunicorn.conf.py 'app:create_app()'
