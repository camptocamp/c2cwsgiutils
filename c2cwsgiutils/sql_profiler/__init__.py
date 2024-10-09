"""
A view (URL=/sql_provider) allowing to enabled/disable a SQL spy.

That runs an "EXPLAIN ANALYZE" on every SELECT query going through SQLAlchemy.
"""

import logging
import warnings

import pyramid.request

from c2cwsgiutils import auth

_ENV_KEY = "C2C_SQL_PROFILER_ENABLED"
_CONFIG_KEY = "c2c.sql_profiler_enabled"
_LOG = logging.getLogger(__name__)


def init(config: pyramid.config.Configurator) -> None:
    """Install a pyramid  event handler that adds the request information, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Install a pyramid  event handler that adds the request information."""
    if auth.is_enabled(config, _ENV_KEY, _CONFIG_KEY):
        from . import _impl  # pylint: disable=import-outside-toplevel

        _impl.init(config)
