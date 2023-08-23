"""
Allows to track the request_id in the logs, the DB and others.

Adds a c2c_request_id attribute to the Pyramid Request class to access it.
"""
import logging
import time
import urllib.parse
import uuid
import warnings
from collections.abc import Mapping
from typing import Optional, Union

import prometheus_client
import pyramid.request
import requests.adapters
import requests.models
from pyramid.threadlocal import get_current_request

from c2cwsgiutils import config_utils, prometheus

ID_HEADERS: list[str] = []
_HTTPAdapter_send = requests.adapters.HTTPAdapter.send
LOG = logging.getLogger(__name__)
DEFAULT_TIMEOUT: Optional[float] = None
_PROMETHEUS_REQUESTS_SUMMARY = prometheus_client.Summary(
    prometheus.build_metric_name("requests"),
    "Requests requests",
    ["scheme", "hostname", "port", "method", "status", "group"],
    unit="seconds",
)


def _gen_request_id(request: pyramid.request.Request) -> str:
    for id_header in ID_HEADERS:
        if id_header in request.headers:
            return request.headers[id_header]  # type: ignore
    return str(uuid.uuid4())


def _patch_requests() -> None:
    def send_wrapper(
        self: requests.adapters.HTTPAdapter,
        request: requests.models.PreparedRequest,
        stream: bool = False,
        timeout: Union[None, float, tuple[float, float], tuple[float, None]] = None,
        verify: Union[bool, str] = True,
        cert: Union[None, bytes, str, tuple[Union[bytes, str], Union[bytes, str]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
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

        assert request.url
        parsed = urllib.parse.urlparse(request.url)
        port = parsed.port or (80 if parsed.scheme == "http" else 443)
        start = time.perf_counter()
        response = _HTTPAdapter_send(
            self, request, timeout=timeout, stream=stream, verify=verify, cert=cert, proxies=proxies
        )

        _PROMETHEUS_REQUESTS_SUMMARY.labels(
            scheme=parsed.scheme,
            hostname=parsed.hostname,
            port=str(port),
            method=request.method,
            status=str(response.status_code),
            group=str(response.status_code // 100 * 100),
        ).observe(time.perf_counter() - start)
        return response

    requests.adapters.HTTPAdapter.send = send_wrapper  # type: ignore[method-assign]


def init(config: Optional[pyramid.config.Configurator] = None) -> None:
    """Initialize the request tracking, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: Optional[pyramid.config.Configurator] = None) -> None:
    """
    Initialize the request tracking.

    Use a X-Request-ID (or other) header to track all the logs related to a request
    including on the sub services.
    """
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
