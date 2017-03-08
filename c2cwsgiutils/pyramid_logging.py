"""
Install a filter on the logging handler to add some info about requests:
  * client_addr
  * method
  * matched_route
  * path

A pyramid event handler is installed to setup this filter for the current request.
"""
import logging
import os
import threading

from cee_syslog_handler import CeeSysLogHandler
import pyramid.events
from pyramid.httpexceptions import HTTPForbidden

LOG = logging.getLogger(__name__)


class _PyramidFilter(logging.Filter):
    """
    A logging filter that adds request information to CEE logs.
    """
    def __init__(self):
        logging.Filter.__init__(self)
        self.context = threading.local()

    def filter(self, record):
        request = getattr(self.context, "request", None)
        if request is not None:
            record.client_addr = request.client_addr
            record.method = request.method
            if request.matched_route is not None:
                record.matched_route = request.matched_route.name
            record.path = request.path
        return True

    def set_context(self, request):
        self.context.request = request


_PYRAMID_FILTER = _PyramidFilter()


class PyramidCeeSysLogHandler(CeeSysLogHandler):
    """
    A CEE (JSON format) log handler with additional information about the current request.
    """
    def __init__(self, *args):
        CeeSysLogHandler.__init__(self, *args)
        self.addFilter(_PYRAMID_FILTER)


def _set_context(event):
    _PYRAMID_FILTER.set_context(event.request)


def install_subscriber(config):
    """
    Install a pyramid  event handler that adds the request information
    """
    config.add_subscriber(_set_context, pyramid.events.NewRequest)

    if 'LOG_VIEW_SECRET' in os.environ:
        config.add_route("logging_level", r"/logging/level", request_method="GET")
        config.add_view(_logging_change_level, route_name="logging_level", renderer="json", http_cache=0)
        LOG.info("Enabled the /logging/change_level API")


def _logging_change_level(request):
    if request.params.get('secret') != os.environ['LOG_VIEW_SECRET']:
        raise HTTPForbidden('Missing or invalid secret parameter')
    name = request.params['name']
    level = request.params.get('level')
    logger = logging.getLogger(name)
    if level is not None:
        LOG.critical("Logging of %s changed from %s to %s", name, logging.getLevelName(logger.level), level)
        logger.setLevel(level)
    return {'status': 200, 'name': name, 'level': logging.getLevelName(logger.level),
            'effective_level': logging.getLevelName(logger.getEffectiveLevel())}
