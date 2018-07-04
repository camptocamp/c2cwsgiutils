import logging
import pyramid.config
import pyramid.request
from typing import Mapping, Any

from c2cwsgiutils import _utils, _auth, broadcast

LOG = logging.getLogger(__name__)
DEPRECATED_CONFIG_KEY = 'c2c.log_view_secret'
DEPRECATED_ENV_KEY = 'LOG_VIEW_SECRET'
CONFIG_KEY = 'c2c.log_view_enabled'
ENV_KEY = 'C2C_LOG_VIEW_ENABLED'


def install_subscriber(config: pyramid.config.Configurator) -> None:
    """
    Install the view to configure the loggers, if configured to do so.
    """
    if _utils.env_or_config(config, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY, False) or \
            _auth.is_enabled(config, ENV_KEY, CONFIG_KEY):
        broadcast.subscribe('c2c_logging_level', lambda name, level: logging.getLogger(name).setLevel(level))

        config.add_route("c2c_logging_level", _utils.get_base_path(config) + r"/logging/level",
                         request_method="GET")
        config.add_view(_logging_change_level, route_name="c2c_logging_level", renderer="fast_json",
                        http_cache=0)
        LOG.info("Enabled the /logging/change_level API")


def _logging_change_level(request: pyramid.request.Request) -> Mapping[str, Any]:
    _auth.auth_view(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)
    name = request.params['name']
    level = request.params.get('level')
    logger = logging.getLogger(name)
    if level is not None:
        LOG.critical("Logging of %s changed from %s to %s", name, logging.getLevelName(logger.level), level)
        logger.setLevel(level)
        broadcast.broadcast('c2c_logging_level', params={'name': name, 'level': level})
    return {'status': 200, 'name': name, 'level': logging.getLevelName(logger.level),
            'effective_level': logging.getLevelName(logger.getEffectiveLevel())}
