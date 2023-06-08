"""Generate statsd metrics for pyramid and SQLAlchemy events."""

import warnings

import pyramid.config
import pyramid.request

from c2cwsgiutils.stats_pyramid import _pyramid_spy


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the whole stats module, for backward compatibility."""

    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """
    Initialize the whole stats pyramid module.

    Arguments:

        config: The Pyramid config
    """

    _pyramid_spy.init(config)
    init_db_spy()


def init_db_spy() -> None:
    """Initialize the database spy."""

    from . import _db_spy

    _db_spy.init()
