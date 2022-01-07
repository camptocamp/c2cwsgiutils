"""
Used by standalone (non-wsgi) processes to setup all the bits and pieces of c2cwsgiutils that could be useful.

Must be imported at the very beginning of the process' life, before any other module is imported.
"""


from plaster.loaders import setup_logging

from c2cwsgiutils import (
    broadcast,
    coverage_setup,
    debug,
    redis_stats,
    request_tracking,
    sentry,
    stats,
    stats_pyramid,
)

_init = False


def init(config_file: str = "c2c:///app/development.ini") -> None:
    """Initialize all the c2cwsgiutils components."""
    global _init
    if not _init:
        setup_logging(config_file)
        coverage_setup.includeme()
        sentry.includeme()
        broadcast.includeme()
        stats.init_backends()
        request_tracking.includeme()
        redis_stats.includeme()
        stats_pyramid.init_db_spy()
        debug.init_daemon()
        _init = True
