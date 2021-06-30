"""
Module used by c2cwsgiutils-run to provide a WSGI application when starting gunicorn.
"""
from typing import Any, Callable

from c2cwsgiutils import coverage_setup  # pragma: no cover

coverage_setup.init()  # pragma: no cover


def create() -> Callable[[Any, Any], Any]:  # pragma: no cover
    # first import and initialize the wsgi application in order to have the logs setup before importing
    # anything else
    from c2cwsgiutils import wsgi

    main_app = wsgi.create_application()

    # then, we can setup a few filters
    from c2cwsgiutils import client_info, profiler, sentry

    full_all = sentry.filter_wsgi_app(profiler.filter_wsgi_app(client_info.Filter(main_app)))

    # Reduce a bit (10s of MB) the memory used by clearing the pre-cached entries for building
    # stack traces. It will be re-built when needed with only the files needed.
    import linecache

    linecache.clearcache()

    return full_all


application = create()  # pragma: no cover
