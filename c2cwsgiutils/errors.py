"""Install exception views to have nice JSON error pages."""

import logging
import os
import traceback
import warnings
from typing import Any, Callable

import pyramid.request
import sqlalchemy.exc
from cornice import cors
from pyramid.httpexceptions import HTTPError, HTTPException, HTTPRedirection, HTTPSuccessful
from webob.request import DisconnectionError

from c2cwsgiutils import auth, config_utils

_DEVELOPMENT = os.environ.get("DEVELOPMENT", "0") != "0"

_LOG = logging.getLogger(__name__)
_STATUS_LOGGER = {
    401: _LOG.debug,
    500: _LOG.error,
    # The rest are warnings
}


def _crude_add_cors(request: pyramid.request.Request, response: pyramid.response.Response = None) -> None:
    if response is None:
        response = request.response
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = ",".join(
        {request.headers.get("Access-Control-Request-Method", request.method)} | {"OPTIONS", "HEAD"}
    )
    response.headers["Access-Control-Allow-Headers"] = "session-id"
    response.headers["Access-Control-Max-Age"] = "86400"


def _add_cors(request: pyramid.request.Request) -> None:
    services = request.registry.cornice_services
    if request.matched_route is not None:
        pattern = request.matched_route.pattern
        service = services.get(pattern, None)
        if service is not None:
            request.info["cors_checked"] = False
            cors.apply_cors_post_request(service, request, request.response)
            return
    _crude_add_cors(request)


def _do_error(
    request: pyramid.request.Request,
    status: int,
    exception: Exception,
    logger: Callable[..., None] = _LOG.error,
    reduce_info_sent: Callable[[Exception], None] = lambda e: None,
) -> pyramid.response.Response:
    logger(
        "%s %s returned status code %s",
        request.method,
        request.url,
        status,
        extra={"referrer": request.referrer},
        exc_info=exception,
    )

    request.response.status_code = status
    _add_cors(request)

    include_dev_details = _include_dev_details(request)
    if not include_dev_details:
        reduce_info_sent(exception)

    response = {"message": str(exception), "status": status}

    if include_dev_details:
        trace = traceback.format_exc()
        response["stacktrace"] = trace
    return response


def _http_error(exception: HTTPException, request: pyramid.request.Request) -> Any:
    if request.method != "OPTIONS":
        log = _STATUS_LOGGER.get(exception.status_code, _LOG.warning)
        log(
            "%s %s returned status code %s: %s",
            request.method,
            request.url,
            exception.status_code,
            str(exception),
            extra={"referrer": request.referrer},
        )
        request.response.headers.update(exception.headers)  # forward headers
        _add_cors(request)
        request.response.status_code = exception.status_code
        return {"message": str(exception), "status": exception.status_code}
    else:
        _crude_add_cors(request)
        request.response.status_code = 200
        return request.response


def _include_dev_details(request: pyramid.request.Request) -> bool:
    return _DEVELOPMENT or auth.is_auth(request)


def _integrity_error(
    exception: sqlalchemy.exc.StatementError, request: pyramid.request.Request
) -> pyramid.response.Response:
    def reduce_info_sent(e: Exception) -> None:
        if isinstance(e, sqlalchemy.exc.StatementError):
            # remove details (SQL statement and links to SQLAlchemy) from the error
            e.statement = None
            e.code = None

    return _do_error(request, 400, exception, reduce_info_sent=reduce_info_sent)


def _client_interrupted_error(
    exception: Exception, request: pyramid.request.Request
) -> pyramid.response.Response:
    # No need to cry wolf if it's just the client that interrupted the connection
    return _do_error(request, 500, exception, logger=_LOG.info)


def _boto_client_error(exception: Any, request: pyramid.request.Request) -> pyramid.response.Response:
    if (
        "ResponseMetadata" in exception.response
        and "HTTPStatusCode" in exception.response["ResponseMetadata"]
    ):
        status_code = exception.response["ResponseMetadata"]["HTTPStatusCode"]
    else:
        status_code = int(exception.response["Error"]["Code"])
    log = _STATUS_LOGGER.get(status_code, _LOG.warning)
    return _do_error(request, status_code, exception, logger=log)


def _other_error(exception: Exception, request: pyramid.request.Request) -> pyramid.response.Response:
    exception_class = exception.__class__.__module__ + "." + exception.__class__.__name__
    if exception_class == "botocore.exceptions.ClientError":
        return _boto_client_error(exception, request)
    status = 500
    if exception_class == "beaker.exceptions.BeakerException" and str(exception) == "Invalid signature":
        status = 401
    _LOG.debug("Actual exception: %s.%s", exception.__class__.__module__, exception.__class__.__name__)
    return _do_error(request, status, exception)


def _passthrough(exception: HTTPException, request: pyramid.request.Request) -> pyramid.response.Response:
    _crude_add_cors(request, exception)
    return exception


def init(config: pyramid.config.Configurator) -> None:
    """Initialize the error views, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme(config)


def includeme(config: pyramid.config.Configurator) -> None:
    """Initialize the error views."""
    if (
        config_utils.env_or_config(
            config, "C2C_ENABLE_EXCEPTION_HANDLING", "c2c.enable_exception_handling", "0"
        )
        != "0"
    ):
        for exception in (HTTPSuccessful, HTTPRedirection):
            config.add_view(view=_passthrough, context=exception, http_cache=0)
        common_options = {"renderer": "json", "http_cache": 0}
        config.add_view(view=_http_error, context=HTTPError, **common_options)

        for exception in (sqlalchemy.exc.IntegrityError, sqlalchemy.exc.DataError):
            config.add_view(view=_integrity_error, context=exception, **common_options)

        # We don't want to cry wolf if the user interrupted the upload of the body
        for exception in (ConnectionResetError, DisconnectionError):
            config.add_view(view=_client_interrupted_error, context=exception, **common_options)

        config.add_view(view=_other_error, context=Exception, **common_options)
        _LOG.info("Installed the error catching views")
