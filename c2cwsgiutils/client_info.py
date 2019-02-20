"""
Small WSGI filter that interprets headers added by proxies to fix some values available in the request.
"""
import re
from typing import Callable, Dict, Any


SEP_RE = re.compile(r', *')


class Filter:
    def __init__(self, application: Callable):
        self._application = application

    def __call__(self, environ: Dict[str, str], start_response: Any) -> Any:
        print(repr(environ))
        if 'HTTP_FORWARDED' in environ:
            forwarded = SEP_RE.split(environ.pop('HTTP_FORWARDED'))[0]
            fields = dict(tuple(f.split('=', maxsplit=1)) for f in forwarded.split(";"))  # type: ignore
            if 'for' in fields:
                environ['REMOTE_ADDR'] = fields['for']
            if 'host' in fields:
                environ['HTTP_HOST'] = fields['host']
            if 'proto' in fields:
                environ['wsgi.url_scheme'] = fields['proto']

        # the rest is taken from paste.deploy.config.PrefixMiddleware
        if 'HTTP_X_FORWARDED_SERVER' in environ:
            environ['SERVER_NAME'] = environ['HTTP_HOST'] = \
                environ.pop('HTTP_X_FORWARDED_SERVER').split(',')[0]
        if 'HTTP_X_FORWARDED_HOST' in environ:
            environ['HTTP_HOST'] = environ.pop('HTTP_X_FORWARDED_HOST').split(',')[0]
        if 'HTTP_X_FORWARDED_FOR' in environ:
            environ['REMOTE_ADDR'] = environ.pop('HTTP_X_FORWARDED_FOR').split(',')[0]
        if 'HTTP_X_FORWARDED_SCHEME' in environ:
            environ['wsgi.url_scheme'] = environ.pop('HTTP_X_FORWARDED_SCHEME')
        elif 'HTTP_X_FORWARDED_PROTO' in environ:
            environ['wsgi.url_scheme'] = environ.pop('HTTP_X_FORWARDED_PROTO')

        return self._application(environ, start_response)
