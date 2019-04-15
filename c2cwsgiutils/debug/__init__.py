import pyramid.config
from typing import Optional

from c2cwsgiutils import _utils, auth

CONFIG_KEY = 'c2c.debug_view_enabled'
ENV_KEY = 'C2C_DEBUG_VIEW_ENABLED'


def init(config: pyramid.config.Configurator) -> None:
    if auth.is_enabled(config, ENV_KEY, CONFIG_KEY):
        from . import _views
        init_daemon(config)
        _views.init(config)


def init_daemon(config: Optional[pyramid.config.Configurator] = None) -> None:
    """
    Initialize the debug broadcast listeners. Used mostly for headless processes that depend on a master
    providing a normal REST API and broadcasting those requests.
    """
    if _utils.env_or_config(config, ENV_KEY, CONFIG_KEY, type_=_utils.config_bool):
        from . import _listeners
        _listeners.init()
