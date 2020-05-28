import logging

import requests
from pyramid.httpexceptions import HTTPForbidden, HTTPMovedPermanently, HTTPNoContent, HTTPUnauthorized

from c2cwsgiutils import sentry, services
from c2cwsgiutils.stats import increment_counter, set_gauge, timer_context
from c2cwsgiutils_app import models

ping_service = services.create("ping", "/ping")
hello_service = services.create("hello", "/hello", cors_credentials=True)
error_service = services.create("error", "/error")
tracking_service = services.create("tracking", "/tracking/{depth:[01]}")
empty_service = services.create("empty", "/empty")
timeout_service = services.create("timeout", "timeout/{where:sql}")
leaked_objects = []


@ping_service.get()
def ping(_):
    global leaked_objects
    leaked_objects.append(object())  # a memory leak to test debug/memory_diff
    logging.getLogger(__name__ + ".ping").info("Ping!")
    return {"pong": True}


@hello_service.get()
def hello_get(_):
    """
    Will use the slave
    """
    with timer_context(["sql", "read_hello"]):
        hello = models.DBSession.query(models.Hello).first()
    increment_counter(["test", "counter"])
    set_gauge(["test", "gauge/s"], 42, tags={"value": 24, "toto": "tutu"})
    return {"value": hello.value}


@hello_service.put()
def hello_put(_):
    """
    Will use the master
    """
    with sentry.capture_exceptions():
        hello = models.DBSession.query(models.Hello).first()
        return {"value": hello.value}


@hello_service.post()
def hello_post(request):
    """
    Will use the slave (overridden by the config).
    """
    return hello_put(request)


@error_service.get()
def error(request):
    code = int(request.params.get("code", "500"))
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
            models.DBSession.add(models.Hello(value="toto"))
    elif request.params.get("db", "0") == "data":
        models.DBSession.add(models.Hello(id="abcd", value="toto"))
    else:
        raise Exception("boom")
    return {"status": 200}


@tracking_service.get()
def tracking(request):
    depth = int(request.matchdict.get("depth"))
    result = {"request_id": request.c2c_request_id}
    if depth > 0:
        result["sub"] = requests.get("http://localhost:8080/api/tracking/%d" % (depth - 1)).json()
    return result


@empty_service.put()
def empty(request):
    request.response.status_code = 204
    return request.response


@timeout_service.get(match_param="where=sql")
def timeout_sql(request):
    models.DBSession.execute("SELECT pg_sleep(2)")
    request.response.status_code = 204
    return request.response
