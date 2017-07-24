from c2cwsgiutils import services
from pyramid.httpexceptions import HTTPForbidden

from c2cwsgiutils.stats import timer_context, increment_counter, set_gauge
from c2cwsgiutils_app import models


ping_service = services.create("ping", "/ping")
hello_service = services.create("hello", "/hello", cors_credentials=True)
error_service = services.create("error", "/error")


@ping_service.get()
def ping(request):
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
