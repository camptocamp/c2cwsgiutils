"""
Used by standalone (non-wsgi) processes to setup all the bits and pieces of c2cwsgiutils that
could be useful.

Must be imported at the very beginning of the process' life, before any other module is imported.
"""
from c2cwsgiutils import pyramid_logging, coverage_setup, sentry, broadcast, stats, redis_stats, stats_pyramid


pyramid_logging.init()
coverage_setup.init()
sentry.init()
broadcast.init()
stats.init_backends()
redis_stats.init()
stats_pyramid.init_db_spy()
