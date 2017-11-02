"""
Module used by c2cwsgiutils_run.sh to provide a WSGI application when starting gunicorn
"""
from typing import Callable  # pragma: no cover
from c2cwsgiutils import coverage_setup  # pragma: no cover
coverage_setup.init()  # pragma: no cover


def _create() -> Callable:  # pragma: no cover
    from c2cwsgiutils import wsgi, sentry
    return sentry.filter_wsgi_app(wsgi.create_application())


def create() -> Callable:  # pragma: no cover
    from c2cwsgiutils import _patches
    _patches.init()  # pragma: no cover
    return _create()


application = create()  # pragma: no cover
