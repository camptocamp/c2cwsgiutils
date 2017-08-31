"""
Allows to track the request_id in the logs, the DB and others. Adds a c2c_request_id attribute
to the Pyramid Request class to access it.
"""
from pyramid.threadlocal import get_current_request
import sqlalchemy.event
from sqlalchemy.orm import Session
import uuid

from c2cwsgiutils import _utils

ID_HEADERS = []
X_VARNISH_OFFSET = 0


def _gen_request_id(request):
    for id_header in ID_HEADERS:
        if id_header in request.headers:
            value = request.headers[id_header]
            if id_header == 'X-Varnish' and value.isdigit():
                # Varnish is weird and sends us an ID incremented by one compared to what it logs
                value = str(int(value) + X_VARNISH_OFFSET)
            return value
    return str(uuid.uuid4())


def _add_session_id(session, _transaction, _connection):
    request = get_current_request()
    if request is not None:
        session.execute("set application_name=:session_id", params={'session_id': request.c2c_request_id})


def init(config):
    global ID_HEADERS, X_VARNISH_OFFSET
    X_VARNISH_OFFSET = int(_utils.env_or_config(config, "C2C_X_VARNISH_OFFSET", 'c2c.x_varnish_offset', "0"))
    ID_HEADERS = ['X-Request-ID', 'X-Correlation-ID', 'Request-ID', 'X-Varnish', 'X-Amzn-Trace-Id']
    extra_header = _utils.env_or_config(config, 'C2C_REQUEST_ID_HEADER', 'c2c.request_id_header')
    if extra_header is not None:
        ID_HEADERS.insert(0, extra_header)

    config.add_request_method(_gen_request_id, 'c2c_request_id', reify=True)

    if _utils.env_or_config(config, 'C2C_SQL_REQUEST_ID', 'c2c.sql_request_id', False):
        sqlalchemy.event.listen(Session, "after_begin", _add_session_id)
