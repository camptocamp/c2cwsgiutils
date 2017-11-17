"""
Install a filter on the logging handler to add some info about requests:
  * client_addr
  * method
  * matched_route
  * path

A pyramid event handler is installed to setup this filter for the current request.
"""
import cee_syslog_handler
import json
import logging
from pyramid.threadlocal import get_current_request
import socket
from typing import Any, MutableMapping, Mapping, IO

LOG = logging.getLogger(__name__)


class _PyramidFilter(logging.Filter):
    """
    A logging filter that adds request information to CEE logs.
    """
    def filter(self, record: Any) -> bool:
        request = get_current_request()
        if request is not None:
            record.client_addr = request.client_addr
            record.method = request.method
            if request.matched_route is not None:
                record.matched_route = request.matched_route.name
            record.path = request.path
            record.request_id = request.c2c_request_id
        record.level_name = record.levelname
        return True


_PYRAMID_FILTER = _PyramidFilter()


def _un_underscore(message: MutableMapping[str, Any]) -> Mapping[str, Any]:
    """
    Elasticsearch is not indexing the fields starting with underscore and cee_syslog_handler is starting
    a lot of interesting fields with underscore. Therefore, it's a good idea to remove all those underscore
    prefixes.
    """
    for key, value in list(message.items()):
        if key.startswith('_'):
            new_key = key[1:]
            if new_key not in message:
                del message[key]
                message[new_key] = value
    return message


def _make_message_dict(*args: Any, **kargv: Any) -> Mapping[str, Any]:
    """
    patch cee_syslog_handler to rename message->full_message otherwise this part is dropped by syslog.
    """
    msg = cee_syslog_handler.make_message_dict(*args, **kargv)
    if msg['message'] != msg['short_message']:
        # only output full_message if it's different from short message
        msg['full_message'] = msg['message']
    del msg['message']
    return _un_underscore(msg)


class PyramidCeeSysLogHandler(cee_syslog_handler.CeeSysLogHandler):
    """
    A CEE (JSON format) log handler with additional information about the current request.
    """
    def __init__(self, *args: Any, **kargv: Any) -> None:
        super().__init__(*args, **kargv)
        self.addFilter(_PYRAMID_FILTER)

    def format(self, record: Any) -> str:
        message = _make_message_dict(record, self._fqdn, self._debugging_fields, self._extra_fields,
                                     self._facility, self._static_fields)
        return ": @cee: %s" % json.dumps(message)


class JsonLogHandler(logging.StreamHandler):
    """
    Log to stdout in JSON.
    """
    def __init__(self, stream: IO=None) -> None:
        super().__init__(stream)
        self.addFilter(_PYRAMID_FILTER)
        self._fqdn = socket.getfqdn()

    def format(self, record: Any) -> str:
        message = _make_message_dict(record,  self._fqdn, debugging_fields=True, extra_fields=True,
                                     facility=None, static_fields={})
        return json.dumps(message)
