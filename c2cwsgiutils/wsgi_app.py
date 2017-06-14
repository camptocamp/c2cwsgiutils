"""
Module used by c2cwsgiutils_run.sh to provide a WSGI application when starting gunicorn
"""
from c2cwsgiutils import coverage_setup  # pragma: no cover
coverage_setup.init()  # pragma: no cover


def create():  # pragma: no cover
    from c2cwsgiutils import wsgi
    return wsgi.create_application()


application = create()  # pragma: no cover
