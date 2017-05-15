"""
Install a filter on the logging handler to add some info about requests:
  * client_addr
  * method
  * matched_route
  * path

A pyramid event handler is installed to setup this filter for the current request.
"""
import logging
import uuid

from cee_syslog_handler import CeeSysLogHandler
from pyramid.threadlocal import get_current_request

from c2cwsgiutils import _utils

CONFIG_KEY = 'c2c.log_view_secret'
ENV_KEY = 'LOG_VIEW_SECRET'

LOG = logging.getLogger(__name__)


class _PyramidFilter(logging.Filter):
    """
    A logging filter that adds request information to CEE logs.
    """
    def filter(self, record):
        request = get_current_request()
        if request is not None:
            record.client_addr = request.client_addr
            record.method = request.method
            if request.matched_route is not None:
                record.matched_route = request.matched_route.name
            record.path = request.path
            record.request_id = request.c2c_request_id
        return True


_PYRAMID_FILTER = _PyramidFilter()


class PyramidCeeSysLogHandler(CeeSysLogHandler):
    """
    A CEE (JSON format) log handler with additional information about the current request.
    """
    def __init__(self, *args):
        CeeSysLogHandler.__init__(self, *args)
        self.addFilter(_PYRAMID_FILTER)


def install_subscriber(config):
    """
    Install the view to configure the loggers, if configured to do so.
    """
    config.add_request_method(lambda request: str(uuid.uuid4()), 'c2c_request_id', reify=True)
    if _utils.env_or_config(config, ENV_KEY, CONFIG_KEY, False):
        config.add_route("c2c_logging_level", _utils.get_base_path(config) + r"/logging/level",
                         request_method="GET")
        config.add_view(_logging_change_level, route_name="c2c_logging_level", renderer="json", http_cache=0)
        LOG.info("Enabled the /logging/change_level API")


def _logging_change_level(request):
    _utils.auth_view(request, ENV_KEY, CONFIG_KEY)
    name = request.params['name']
    level = request.params.get('level')
    logger = logging.getLogger(name)
    if level is not None:
        LOG.critical("Logging of %s changed from %s to %s", name, logging.getLevelName(logger.level), level)
        logger.setLevel(level)
    return {'status': 200, 'name': name, 'level': logging.getLevelName(logger.level),
            'effective_level': logging.getLevelName(logger.getEffectiveLevel())}
