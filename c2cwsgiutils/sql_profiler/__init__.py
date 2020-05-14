"""
A view (URL=/sql_provider) allowing to enabled/disable a SQL spy that runs an "EXPLAIN ANALYZE" on
every SELECT query going through SQLAlchemy.
"""
import logging

import pyramid.request

from c2cwsgiutils import auth

ENV_KEY = "C2C_SQL_PROFILER_ENABLED"
CONFIG_KEY = "c2c.sql_profiler_enabled"
LOG = logging.getLogger(__name__)
repository = None


def init(config: pyramid.config.Configurator) -> None:
    """
    Install a pyramid  event handler that adds the request information
    """
    if auth.is_enabled(config, ENV_KEY, CONFIG_KEY):
        from . import _impl

        _impl.init(config)
