###
# app configuration
# https://docs.gunicorn.org/en/stable/settings.html
###
import os

from c2cwsgiutils import get_config_defaults, get_logconfig_dict, get_paste_config

bind = ":8080"

worker_class = "gthread"
workers = os.environ.get("GUNICORN_WORKERS", 2)
threads = os.environ.get("GUNICORN_THREADS", 10)
preload = "true"

paste = get_paste_config()
wsgi_app = paste

accesslog = "-"
access_log_format = os.environ.get(
    "GUNICORN_ACCESS_LOG_FORMAT",
    '%(H)s %({Host}i)s %(m)s %(U)s?%(q)s "%(f)s" "%(a)s" %(s)s %(B)s %(D)s %(p)s',
)

###
# logging configuration
# https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
###
logconfig_dict = get_logconfig_dict(paste)
if os.environ.get("DEBUG_LOGCONFIG", "0") == "1":
    print("LOGCONFIG")
    print(logconfig_dict)

raw_paste_global_conf = ["=".join(e) for e in get_config_defaults().items()]
