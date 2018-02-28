import logging
from pyramid.httpexceptions import HTTPForbidden
import requests

from c2cwsgiutils import services
from c2cwsgiutils import sentry
from c2cwsgiutils.stats import timer_context, increment_counter, set_gauge
from c2cwsgiutils_app import models


ping_service = services.create("ping", "/ping")
hello_service = services.create("hello", "/hello", cors_credentials=True)
error_service = services.create("error", "/error")
tracking_service = services.create("tracking", "/tracking/{depth:[01]}")
empty_service = services.create("empty", "/empty")
leaked_objects = []


class LeakedObject(object):
    pass


@ping_service.get()
def ping(request):
    global leaked_objects
    leaked_objects.append(LeakedObject())  # a memory leak to test debug/memory_diff
    logging.getLogger(__name__+".ping").info("Ping!")
    return {'pong': True}


@hello_service.get()
def hello_get(request):
    """
    Will use the slave
    """
    with timer_context(['sql', 'read_hello']):
        hello = models.DBSession.query(models.Hello).first()
    increment_counter(['test', 'counter'])
    set_gauge(['test', 'gauge/s'], 42)
    return {'value': hello.value}


@hello_service.put()
def hello_put(request):
    """
    Will use the master
    """
    with sentry.capture_exceptions():
        hello = models.DBSession.query(models.Hello).first()
        return {'value': hello.value}


@hello_service.post()
def hello_post(request):
    """
    Will use the slave (overridden by the config).
    """
    return hello_put(request)


@error_service.get()
def error(request):
    code = int(request.params.get('code', '500'))
    if code == 403:
        raise HTTPForbidden('bam')
    elif request.params.get('db', '0') == '1':
        for _ in range(2):
            models.DBSession.add(models.Hello(value='toto'))
    else:
        raise Exception('boom')
    return {'status': 200}


@tracking_service.get()
def tracking(request):
    depth = int(request.matchdict.get('depth'))
    result = {'request_id': request.c2c_request_id}
    if depth > 0:
        result['sub'] = requests.get('http://localhost/api/tracking/%d' % (depth - 1)).json()
    return result


@empty_service.put()
def empty(request):
    request.response.status_code = 204
    return request.response
