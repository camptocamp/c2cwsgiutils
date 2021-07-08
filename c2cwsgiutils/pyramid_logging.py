"""
Install a filter on the logging handler to add some info about requests:

  * client_addr
  * method
  * matched_route
  * path

A pyramid event handler is installed to setup this filter for the current request.
"""
import json
import logging
import logging.config
import os
import socket
import sys
from typing import IO, Any, Dict, Mapping, MutableMapping, Optional, Set

import cee_syslog_handler
from pyramid.threadlocal import get_current_request

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
    Elasticsearch is not indexing the fields starting with underscore and cee_syslog_handler is starting a lot
    of interesting fields with underscore.

    Therefore, it's a good idea to remove all those underscore prefixes.
    """
    for key, value in list(message.items()):
        if key.startswith("_"):
            new_key = key[1:]
            if new_key not in message:
                del message[key]
                message[new_key] = value
    return message


def _rename_field(dico: MutableMapping[str, Any], source: str, dest: str) -> None:
    if source in dico:
        dico[dest] = dico[source]
        del dico[source]


def _make_message_dict(*args: Any, **kargv: Any) -> Mapping[str, Any]:
    """
    patch cee_syslog_handler to rename message->full_message otherwise this part is dropped by syslog.
    """
    msg = cee_syslog_handler.make_message_dict(*args, **kargv)
    if msg["message"] != msg["short_message"]:
        # only output full_message if it's different from short message
        msg["full_message"] = msg["message"]
        msg["full_msg"] = "true"
    del msg["message"]

    # make the output more consistent with the one from java
    _rename_field(msg, "short_message", "msg")
    _rename_field(msg, "facility", "logger_name")

    return _un_underscore(msg)


class PyramidCeeSysLogHandler(cee_syslog_handler.CeeSysLogHandler):  # type: ignore
    """
    A CEE (JSON format) log handler with additional information about the current request.
    """

    def __init__(self, *args: Any, **kargv: Any) -> None:
        super().__init__(*args, **kargv)
        self.addFilter(_PYRAMID_FILTER)

    def format(self, record: Any) -> str:
        message = _make_message_dict(
            record,
            self._fqdn,
            self._debugging_fields,
            self._extra_fields,
            self._facility,
            self._static_fields,
        )
        return ": @cee: %s" % json.dumps(message)


class JsonLogHandler(logging.StreamHandler):
    """
    Log to stdout in JSON.
    """

    def __init__(self, stream: Optional[IO[str]] = None):
        super().__init__(stream)
        self.addFilter(_PYRAMID_FILTER)
        self._fqdn = socket.getfqdn()

    def format(self, record: Any) -> str:
        message = _make_message_dict(
            record, self._fqdn, debugging_fields=True, extra_fields=True, facility=None, static_fields={}
        )
        return json.dumps(message)


def get_defaults() -> Dict[str, str]:
    """
    Get the logging configuration variables
    """
    results = {}
    lowercase_keys: Set[str] = set()
    for key, value in os.environ.items():
        if key.lower() in lowercase_keys:
            LOG.warning("The environment variable '%s' is duplicated with different case, ignoring", key)
            continue
        lowercase_keys.add(key.lower())
        results[key] = value
    return results


def init(configfile: Optional[str] = None) -> Optional[str]:
    logging.captureWarnings(True)
    configfile_ = (
        configfile if configfile is not None else os.environ.get("C2CWSGIUTILS_CONFIG", "/app/production.ini")
    )
    if os.path.isfile(configfile_):
        logging.config.fileConfig(configfile_, defaults=get_defaults())
        return configfile_
    else:
        level = os.environ.get("LOG_LEVEL", os.environ.get("OTHER_LOG_LEVEL", "INFO"))
        if os.environ.get("LOG_TYPE") == "json":
            root = logging.getLogger()
            handler = JsonLogHandler(stream=sys.stdout)
            handler.setLevel(logging.NOTSET)
            root.addHandler(handler)
            root.setLevel(level)
        else:
            logging.basicConfig(
                level=level, format="%(asctime)-15s %(levelname)5s %(name)s %(message)s", stream=sys.stderr
            )
        return None
