"""Generate statsd metrics for pyramid and SQLAlchemy events."""
import warnings

import pyramid.config
import pyramid.request
<<<<<<< HEAD

from c2cwsgiutils import stats
||||||| parent of 7d860b4 (Continue)
from c2cwsgiutils import stats
=======

from c2cwsgiutils import metrics_stats
>>>>>>> 7d860b4 (Continue)


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the whole stats module, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """
    Initialize the whole stats module.

    Arguments:

        config: The Pyramid config
    """
    stats.init_backends(config.get_settings())
    if stats.BACKENDS:  # pragma: nocover
        if "memory" in stats.BACKENDS:  # pragma: nocover
            from . import _views

            _views.init(config)
        from . import _pyramid_spy

        _pyramid_spy.init(config)
        init_db_spy()


def init_db_spy() -> None:
    """Initialize the database spy."""
    from . import _db_spy

    _db_spy.init()
