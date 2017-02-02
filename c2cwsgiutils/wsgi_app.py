"""
Module used by c2cwsgiutils_run.sh to provide a WSGI application when starting gunicorn
"""
from c2cwsgiutils import wsgi


application = wsgi.create_application()
