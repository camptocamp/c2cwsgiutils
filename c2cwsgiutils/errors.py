"""
Install exception views to have nice JSON error pages.
"""
from cornice import cors
import logging
import os
import pyramid.config
import pyramid.request
from pyramid.httpexceptions import HTTPException
import sqlalchemy.exc
import traceback
from typing import Any, Callable
from webob.request import DisconnectionError

from c2cwsgiutils import _utils, _auth

DEVELOPMENT = os.environ.get('DEVELOPMENT', '0') != '0'
DEPRECATED_CONFIG_KEY = 'c2c.error_details_secret'
DEPRECATED_ENV_KEY = 'ERROR_DETAILS_SECRET'

LOG = logging.getLogger(__name__)
STATUS_LOGGER = {
    400: LOG.info,
    401: LOG.info,
    500: LOG.error
    # The rest are warnings
}


def _crude_add_cors(request: pyramid.request.Request) -> None:
    response = request.response
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = \
        ','.join({request.headers.get('Access-Control-Request-Method', request.method)} | {'OPTIONS', 'HEAD'})
    response.headers['Access-Control-Allow-Headers'] = "session-id"
    response.headers['Access-Control-Max-Age'] = "86400"


def _add_cors(request: pyramid.request.Request) -> None:
    services = request.registry.cornice_services
    if request.matched_route is not None:
        pattern = request.matched_route.pattern
        service = services.get(pattern, None)
        if service is not None:
            request.info['cors_checked'] = False
            return cors.apply_cors_post_request(service, request, request.response)
    _crude_add_cors(request)


def _do_error(request: pyramid.request.Request, status: int, exception: Exception,
              logger: Callable=LOG.error,
              reduce_info_sent: Callable[[Exception], None] = lambda e: None) -> pyramid.response.Response:
    logger("%s %s returned status code %s",
           request.method, request.url, status,
           extra={'referer': request.referer}, exc_info=exception)

    request.response.status_code = status
    _add_cors(request)

    include_dev_details = _include_dev_details(request)
    if not include_dev_details:
        reduce_info_sent(exception)

    response = {"message": str(exception), "status": status}

    if include_dev_details:
        trace = traceback.format_exc()
        response['stacktrace'] = trace
    return response


def _http_error(exception: HTTPException, request: pyramid.request.Request) -> Any:
    log = STATUS_LOGGER.get(exception.status_code, LOG.warning)
    log("%s %s returned status code %s: %s",
        request.method, request.url, exception.status_code, str(exception),
        extra={'referer': request.referer})
    if request.method != 'OPTIONS':
        request.response.status_code = exception.status_code
        _add_cors(request)
        return {"message": str(exception), "status": exception.status_code}
    else:
        _crude_add_cors(request)
        request.response.status_code = 200


def _include_dev_details(request: pyramid.request.Request) -> bool:
    return DEVELOPMENT or _auth.is_auth(request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY)


def _integrity_error(exception: sqlalchemy.exc.StatementError,
                     request: pyramid.request.Request) -> pyramid.response.Response:
    def reduce_info_sent(e: sqlalchemy.exc.StatementError) -> None:
        # remove details (SQL statement and links to SQLAlchemy) from the error
        e.statement = None
        e.code = None
    return _do_error(request, 400, exception, reduce_info_sent=reduce_info_sent)


def _client_interrupted_error(exception: Exception,
                              request: pyramid.request.Request) -> pyramid.response.Response:
    # No need to cry wolf if it's just the client that interrupted the connection
    return _do_error(request, 500, exception, logger=LOG.info)


def _boto_client_error(exception: Any, request: pyramid.request.Request) -> pyramid.response.Response:
    if 'ResponseMetadata' in exception.response and \
            'HTTPStatusCode' in exception.response['ResponseMetadata']:
        status_code = exception.response['ResponseMetadata']['HTTPStatusCode']
    else:
        status_code = int(exception.response['Error']['Code'])
    log = STATUS_LOGGER.get(status_code, LOG.warning)
    return _do_error(request, status_code, exception, logger=log)


def _other_error(exception: Exception, request: pyramid.request.Request) -> pyramid.response.Response:
    if exception.__class__.__module__ == 'botocore.exceptions' and \
            exception.__class__.__name__ == 'ClientError':
        return _boto_client_error(exception, request)
    LOG.debug("Actual exception: %s.%s", exception.__class__.__module__, exception.__class__.__name__)
    return _do_error(request, 500, exception)


def init(config: pyramid.config.Configurator) -> None:
    if _utils.env_or_config(config, 'C2C_DISABLE_EXCEPTION_HANDLING',
                            'c2c.disable_exception_handling', '0') == '0':
        common_options = {'renderer': 'json', 'http_cache': 0}
        config.add_view(view=_http_error, context=HTTPException, **common_options)
        config.add_view(view=_integrity_error, context=sqlalchemy.exc.IntegrityError, **common_options)
        config.add_view(view=_integrity_error, context=sqlalchemy.exc.DataError, **common_options)

        # We don't want to cry wolf if the user interrupted the uplad of the body
        config.add_view(view=_client_interrupted_error, context=ConnectionResetError, **common_options)
        config.add_view(view=_client_interrupted_error, context=DisconnectionError, **common_options)

        config.add_view(view=_other_error, context=Exception, **common_options)
        LOG.info('Installed the error catching views')
