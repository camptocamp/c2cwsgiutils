import c2cwsgiutils.pyramid
from pyramid.config import Configurator

from c2cwsgiutils_app import models


def main(_, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, route_prefix='/api')
    config.add_settings(handle_exceptions=False)
    config.include(c2cwsgiutils.pyramid.includeme)
    models.init(config)
    config.scan("c2cwsgiutils_app.services")

    return config.make_wsgi_app()
