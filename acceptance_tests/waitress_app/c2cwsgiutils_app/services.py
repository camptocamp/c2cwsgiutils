import logging

import prometheus_client
import requests
import sqlalchemy.sql.expression
from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPForbidden,
    HTTPMovedPermanently,
    HTTPNoContent,
    HTTPUnauthorized,
)

from c2cwsgiutils import sentry, services
from c2cwsgiutils_app import models

_PROMETHEUS_TEST_COUNTER = prometheus_client.Counter("test_counter", "Test counter")
_PROMETHEUS_TEST_GAUGE = prometheus_client.Gauge("test_gauge", "Test gauge", ["value", "toto"])
_PROMETHEUS_TEST_SUMMARY = prometheus_client.Summary("test_summary", "Test summary")


ping_service = services.create("ping", "/ping")
hello_service = services.create("hello", "/hello", cors_credentials=True)
error_service = services.create("error", "/error")
tracking_service = services.create("tracking", "/tracking/{depth:[01]}")
empty_service = services.create("empty", "/empty")
timeout_service = services.create("timeout", "timeout/{where:sql}")
leaked_objects = []


class LeakedObject:
    pass


@ping_service.get()
def ping(_):
    leaked_objects.append(LeakedObject())  # A memory leak to test debug/memory_diff
    logging.getLogger(__name__ + ".ping").info("Ping!")
    return {"pong": True}


@hello_service.get()
def hello_get(request):
    """Will use the slave."""
    with _PROMETHEUS_TEST_SUMMARY.time():
        hello = request.dbsession.query(models.Hello).first()
    _PROMETHEUS_TEST_COUNTER.inc()
    _PROMETHEUS_TEST_GAUGE.labels(value=24, toto="tutu").set(42)
    return {"value": hello.value}


@hello_service.put()
def hello_put(request):
    """Will use the master."""
    with sentry.capture_exceptions():
        hello = request.dbsession.query(models.Hello).first()
        return {"value": hello.value}


@hello_service.post()
def hello_post(request):
    """Will use the slave (overridden by the config)."""
    return hello_put(request)


@error_service.get()
def error(request):
    code = int(request.params.get("code", "500"))
    if code == 400:
        raise HTTPBadRequest("arg")
    if code == 403:
        raise HTTPForbidden("bam")
    if code == 401:
        e = HTTPUnauthorized()
        e.headers["WWW-Authenticate"] = 'Basic realm="Access to staging site"'
        raise e
    if code == 301:
        raise HTTPMovedPermanently(location="http://www.camptocamp.com/en/")
    if code == 204:
        raise HTTPNoContent()
    if request.params.get("db", "0") == "dup":
        for _ in range(2):
            request.dbsession.add(models.Hello(value="toto"))
    elif request.params.get("db", "0") == "data":
        request.dbsession.add(models.Hello(id="abcd", value="toto"))
    else:
        raise Exception("boom")
    return {"status": 200}


@tracking_service.get()
def tracking(request):
    depth = int(request.matchdict.get("depth"))
    result = {"request_id": request.c2c_request_id}
    if depth > 0:
        result["sub"] = requests.get(f"http://localhost:8080/api/tracking/{depth - 1}").json()
    return result


@empty_service.put()
def empty_put(request):
    request.response.status_code = 204
    return request.response


@empty_service.patch()
def empty_patch(request):
    request.response.status_code = 204
    return request.response


@timeout_service.get(match_param="where=sql")
def timeout_sql(request):
    request.dbsession.execute(sqlalchemy.sql.expression.text("SELECT pg_sleep(2)"))
    request.response.status_code = 204
    return request.response
