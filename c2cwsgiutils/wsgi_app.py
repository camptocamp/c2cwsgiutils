"""
Module used by c2cwsgiutils_run.sh to provide a WSGI application when starting gunicorn
"""
from typing import Callable
from c2cwsgiutils import coverage_setup  # pragma: no cover
coverage_setup.init()  # pragma: no cover


def create() -> Callable:  # pragma: no cover
    from c2cwsgiutils import wsgi, sentry
    return sentry.filter_wsgi_app(wsgi.create_application())


application = create()  # pragma: no cover
