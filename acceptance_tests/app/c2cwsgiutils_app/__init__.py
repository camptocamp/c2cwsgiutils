from c2cwsgiutils_app import models
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPInternalServerError

import c2cwsgiutils.pyramid
from c2cwsgiutils import broadcast
from c2cwsgiutils.health_check import HealthCheck, JsonCheckException


def _failure(_request):
    raise HTTPInternalServerError("failing check")


def _failure_json(_request):
    raise JsonCheckException("failing check", {"some": "json"})


@broadcast.decorator(expect_answers=True)
def broadcast_view():
    return 42


def main(_, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, route_prefix="/api")

    # Initialise the broadcast view before c2cwsgiutils is initialised. This allows to test the
    # reconfiguration on the fly of the broadcast framework
    config.add_route("broadcast", r"/broadcast", request_method="GET")
    config.add_view(
        lambda request: broadcast_view(), route_name="broadcast", renderer="fast_json", http_cache=0
    )

    config.include(c2cwsgiutils.pyramid.includeme)
    models.init(config)
    config.scan("c2cwsgiutils_app.services")
    health_check = HealthCheck(config)
    health_check.add_db_session_check(models.DBSession, at_least_one_model=models.Hello)
    health_check.add_url_check("http://localhost:8080/api/hello")
    health_check.add_url_check(name="fun_url", url=lambda _request: "http://localhost:8080/api/hello")
    health_check.add_custom_check("fail", _failure, 2)
    health_check.add_custom_check("fail_json", _failure_json, 2)
    health_check.add_alembic_check(models.DBSession, "/app/alembic.ini", 1)

    return config.make_wsgi_app()
