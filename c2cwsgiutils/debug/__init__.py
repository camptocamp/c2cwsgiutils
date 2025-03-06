import warnings

import pyramid.config

from c2cwsgiutils import auth, config_utils
from c2cwsgiutils.debug import utils

CONFIG_KEY = "c2c.debug_view_enabled"
ENV_KEY = "C2C_DEBUG_VIEW_ENABLED"

# for backward compatibility
get_size = utils.get_size
dump_memory_maps = utils.dump_memory_maps


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the debug tools, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead", stacklevel=2)
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize the debug tools."""
    if auth.is_enabled(config, ENV_KEY, CONFIG_KEY):
        from c2cwsgiutils.debug import _views  # pylint: disable=import-outside-toplevel

        init_daemon(config)
        _views.init(config)


def init_daemon(config: pyramid.config.Configurator | None = None) -> None:
    """
    Initialize the debug broadcast listeners.

    Used mostly for headless processes that depend on a master providing a normal REST API and broadcasting
    those requests.
    """
    if config_utils.env_or_config(config, ENV_KEY, CONFIG_KEY, type_=config_utils.config_bool):
        from c2cwsgiutils.debug import (  # pylint: disable=import-outside-toplevel
            _listeners,
        )

        _listeners.init()
