###
# app configuration
# https://docs.gunicorn.org/en/stable/settings.html
###
import os
import sys
import json
import pprint

from c2cwsgiutils import get_config_defaults, get_logconfig_dict


def _get_paste_config() -> str:
    next_one = False
    for val in sys.argv:
        if next_one:
            return val
        if val in ['--paste', '--paster']:
            next_one = True

    fallback = os.environ.get("C2CWSGIUTILS_CONFIG", "production.ini")
    return fallback



bind = ":8080"

worker_class = "gthread"
workers = os.environ.get("GUNICORN_WORKERS", 2)
threads = os.environ.get("GUNICORN_THREADS", 10)
preload = "true"

paste = _get_paste_config()
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
print('logconfig_dict')
pprint.pprint(logconfig_dict)

raw_paste_global_conf = ["=".join(e) for e in get_config_defaults().items()]
