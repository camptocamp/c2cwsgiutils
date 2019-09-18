"""
Used by standalone (non-wsgi) processes to setup all the bits and pieces of c2cwsgiutils that
could be useful.

Must be imported at the very beginning of the process' life, before any other module is imported.
"""


def _first() -> None:
    from c2cwsgiutils import pyramid_logging
    pyramid_logging.init()


def _second() -> None:
    from c2cwsgiutils import coverage_setup, sentry, broadcast, stats, redis_stats,\
        stats_pyramid, debug, request_tracking
    coverage_setup.init()
    sentry.init()
    broadcast.init()
    stats.init_backends()
    request_tracking.init()
    redis_stats.init()
    stats_pyramid.init_db_spy()
    debug.init_daemon()


_first()
_second()
