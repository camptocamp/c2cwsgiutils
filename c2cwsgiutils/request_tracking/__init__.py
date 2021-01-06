"""
Allows to track the request_id in the logs, the DB and others. Adds a c2c_request_id attribute
to the Pyramid Request class to access it.
"""
import logging
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional, Sequence  # noqa  # pylint: disable=unused-import

import pyramid.request
import requests.adapters
import requests.models
from pyramid.threadlocal import get_current_request

from c2cwsgiutils import config_utils, stats

ID_HEADERS: List[str] = []
_HTTPAdapter_send = requests.adapters.HTTPAdapter.send
LOG = logging.getLogger(__name__)
DEFAULT_TIMEOUT: Optional[float] = None


def _gen_request_id(request: pyramid.request.Request) -> str:
    for id_header in ID_HEADERS:
        if id_header in request.headers:
            return request.headers[id_header]  # type: ignore
    return str(uuid.uuid4())


def _patch_requests() -> None:
    def send_wrapper(
        self: requests.adapters.HTTPAdapter,
        request: requests.models.PreparedRequest,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> requests.Response:
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
            if request.url is not None:
                parsed = urllib.parse.urlparse(request.url)
                port = parsed.port or (80 if parsed.scheme == "http" else 443)
                if stats.USE_TAGS:
                    key: Sequence[Any] = ["requests"]
                    tags: Optional[Dict[str, Any]] = dict(
                        scheme=parsed.scheme,
                        host=parsed.hostname,
                        port=port,
                        method=request.method,
                        status=status,
                    )
                else:
                    key = ["requests", parsed.scheme, parsed.hostname, port, request.method, status]
                    tags = None
                timer.stop(key, tags)

    requests.adapters.HTTPAdapter.send = send_wrapper  # type: ignore


def init(config: Optional[pyramid.config.Configurator] = None) -> None:
    global ID_HEADERS, DEFAULT_TIMEOUT
    ID_HEADERS = ["X-Request-ID", "X-Correlation-ID", "Request-ID", "X-Varnish", "X-Amzn-Trace-Id"]
    if config is not None:
        extra_header = config_utils.env_or_config(config, "C2C_REQUEST_ID_HEADER", "c2c.request_id_header")
        if extra_header:
            ID_HEADERS.insert(0, extra_header)
        config.add_request_method(_gen_request_id, "c2c_request_id", reify=True)

    DEFAULT_TIMEOUT = config_utils.env_or_config(
        config, "C2C_REQUESTS_DEFAULT_TIMEOUT", "c2c.requests_default_timeout", type_=float
    )
    _patch_requests()

    if config_utils.env_or_config(config, "C2C_SQL_REQUEST_ID", "c2c.sql_request_id", False):
        from . import _sql

        _sql.init()
