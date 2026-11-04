"""Small Gunicorn configuration for the one-worker local training service."""

bind = "0.0.0.0:8000"
workers = 1
worker_class = "gthread"
threads = 4
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
keepalive = 2
timeout = 30
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190
worker_tmp_dir = "/tmp"
umask = 0o077
