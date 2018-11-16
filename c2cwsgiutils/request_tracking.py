"""
Allows to track the request_id in the logs, the DB and others. Adds a c2c_request_id attribute
to the Pyramid Request class to access it.
"""
import logging
import pyramid.config
from pyramid.threadlocal import get_current_request
import pyramid.request
import requests.adapters
import requests.models
import sqlalchemy.event
from sqlalchemy.orm import Session
from typing import List, Any, Optional, Dict, Sequence  # noqa  # pylint: disable=unused-import
import uuid
import urllib.parse

from c2cwsgiutils import _utils, stats

ID_HEADERS = []  # type: List[str]
_HTTPAdapter_send = requests.adapters.HTTPAdapter.send
LOG = logging.getLogger(__name__)
DEFAULT_TIMEOUT = None  # type: Optional[float]


def _gen_request_id(request: pyramid.request.Request) -> str:
    for id_header in ID_HEADERS:
        if id_header in request.headers:
            return request.headers[id_header]
    return str(uuid.uuid4())


def _add_session_id(session: Session, _transaction: Any, _connection: Any) -> None:
    request = get_current_request()
    if request is not None:
        session.execute("set application_name=:session_id", params={'session_id': request.c2c_request_id})


def _patch_requests() -> None:
    def send_wrapper(self: requests.adapters.HTTPAdapter, request: requests.models.PreparedRequest,
                     timeout: Optional[float]=None, **kwargs: Any) -> requests.Response:
        pyramid_request = get_current_request()
        header = ID_HEADERS[0]
        if pyramid_request is not None and header not in request.headers:
            request.headers[header] = pyramid_request.c2c_request_id

        if timeout is None:
            if DEFAULT_TIMEOUT is not None:
                timeout = DEFAULT_TIMEOUT
            else:
                LOG.warning("Doing a %s request without timeout to %s", request.method, request.url)

        status = 999
        timer = stats.timer()
        try:
            response = _HTTPAdapter_send(self, request, timeout=timeout, **kwargs)
            status = response.status_code
            return response
        finally:
            parsed = urllib.parse.urlparse(request.url)  # type: ignore
            if stats.USE_TAGS:
                key = ['requests']  # type: Sequence[Any]
                tags = dict(scheme=parsed.scheme, host=parsed.hostname, port=parsed.port,
                            method=request.method, status=status)  # type: Optional[Dict]
            else:
                key = ['requests', parsed.scheme, parsed.hostname, parsed.port, request.method, status]
                tags = None
            timer.stop(key, tags)

    requests.adapters.HTTPAdapter.send = send_wrapper  # type: ignore


def init(config: pyramid.config.Configurator) -> None:
    global ID_HEADERS, DEFAULT_TIMEOUT
    ID_HEADERS = ['X-Request-ID', 'X-Correlation-ID', 'Request-ID', 'X-Varnish', 'X-Amzn-Trace-Id']
    extra_header = _utils.env_or_config(config, 'C2C_REQUEST_ID_HEADER', 'c2c.request_id_header')
    if extra_header is not None:
        ID_HEADERS.insert(0, extra_header)
    DEFAULT_TIMEOUT = _utils.env_or_config(config, 'C2C_REQUESTS_DEFAULT_TIMEOUT',
                                           'c2c.requests_default_timeout', type_=float)

    config.add_request_method(_gen_request_id, 'c2c_request_id', reify=True)
    _patch_requests()

    if _utils.env_or_config(config, 'C2C_SQL_REQUEST_ID', 'c2c.sql_request_id', False):
        sqlalchemy.event.listen(Session, "after_begin", _add_session_id)
