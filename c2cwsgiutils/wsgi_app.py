"""
Module used by c2cwsgiutils_run.sh to provide a WSGI application when starting gunicorn
"""
from typing import Callable
from c2cwsgiutils import coverage_setup  # pragma: no cover
coverage_setup.init()  # pragma: no cover


def create() -> Callable:  # pragma: no cover
    # first import and initialize the wsgi application in order to have the logs setup before importing
    # anything else
    from c2cwsgiutils import wsgi
    main_app = wsgi.create_application()

    # then, we can setup a few filters
    from c2cwsgiutils import sentry, profiler
    return sentry.filter_wsgi_app(profiler.filter_wsgi_app(main_app))


application = create()  # pragma: no cover
