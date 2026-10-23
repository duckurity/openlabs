# Gunicorn production config for the ThreadLine API challenge.

bind = "0.0.0.0:1000"

# Worker math for a 0.5-CPU / 256MB container:
#   2 workers x 4 threads = 8 concurrent requests, ~60MB RSS per worker.
workers = 2
threads = 4
worker_class = "gthread"

timeout = 30
graceful_timeout = 10

accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'

reload = False
