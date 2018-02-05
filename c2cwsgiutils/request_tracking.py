"""
Allows to track the request_id in the logs, the DB and others. Adds a c2c_request_id attribute
to the Pyramid Request class to access it.
"""
import pyramid.config
from pyramid.threadlocal import get_current_request
import pyramid.request
import requests.adapters
import requests.models
import sqlalchemy.event
from sqlalchemy.orm import Session
from typing import List, Any  # noqa  # pylint: disable=unused-import
import uuid

from c2cwsgiutils import _utils

ID_HEADERS = []  # type: List[str]
_HTTPAdapter_send = requests.adapters.HTTPAdapter.send


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
                     **kwargs: Any) -> requests.Response:
        pyramid_request = get_current_request()
        header = ID_HEADERS[0]
        if pyramid_request is not None and header not in request.headers:
            request.headers[header] = pyramid_request.c2c_request_id
        return _HTTPAdapter_send(self, request, **kwargs)

    requests.adapters.HTTPAdapter.send = send_wrapper  # type: ignore


def init(config: pyramid.config.Configurator) -> None:
    global ID_HEADERS
    ID_HEADERS = ['X-Request-ID', 'X-Correlation-ID', 'Request-ID', 'X-Varnish', 'X-Amzn-Trace-Id']
    extra_header = _utils.env_or_config(config, 'C2C_REQUEST_ID_HEADER', 'c2c.request_id_header')
    if extra_header is not None:
        ID_HEADERS.insert(0, extra_header)

    config.add_request_method(_gen_request_id, 'c2c_request_id', reify=True)
    _patch_requests()

    if _utils.env_or_config(config, 'C2C_SQL_REQUEST_ID', 'c2c.sql_request_id', False):
        sqlalchemy.event.listen(Session, "after_begin", _add_session_id)
