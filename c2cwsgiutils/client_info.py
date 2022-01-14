import re
from typing import Any, Callable, Dict

SEP_RE = re.compile(r", *")


class Filter:
    """
    Small WSGI filter that interprets headers added by proxies.

    To fix some values available in the request.
    Concerned headers: Forwarded and the X_Forwarded_* Headers.
    """

    def __init__(self, application: Callable[[Dict[str, str], Any], Any]):
        self._application = application

    def __call__(self, environ: Dict[str, str], start_response: Any) -> Any:
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Forwarded
        if "HTTP_FORWARDED" in environ:
            _handle_forwarded(environ)
        else:
            _handle_others(environ)

        return self._application(environ, start_response)


def _handle_others(environ: Dict[str, str]) -> None:
    # The rest is taken from paste.deploy.config.PrefixMiddleware
    if "HTTP_X_FORWARDED_SERVER" in environ:
        environ["HTTP_ORIGINAL_X_FORWARDED_SERVER"] = environ["HTTP_X_FORWARDED_SERVER"]
        environ["SERVER_NAME"] = environ["HTTP_HOST"] = environ.pop("HTTP_X_FORWARDED_SERVER").split(",")[0]
    if "HTTP_X_FORWARDED_HOST" in environ:
        environ["HTTP_ORIGINAL_X_FORWARDED_HOST"] = environ["HTTP_X_FORWARDED_HOST"]
        environ["HTTP_ORIGINAL_HOST"] = environ["HTTP_HOST"]
        environ["HTTP_HOST"] = environ.pop("HTTP_X_FORWARDED_HOST").split(",")[0]
    if "HTTP_X_FORWARDED_FOR" in environ:
        environ["HTTP_ORIGINAL_X_FORWARDED_FOR"] = environ["HTTP_X_FORWARDED_FOR"]
        environ["REMOTE_ADDR"] = environ.pop("HTTP_X_FORWARDED_FOR").split(",")[0]
    if "HTTP_X_FORWARDED_SCHEME" in environ:
        environ["HTTP_ORIGINAL_X_FORWARDED_SCHEME"] = environ["HTTP_X_FORWARDED_SCHEME"]
        environ["wsgi.url_scheme"] = environ.pop("HTTP_X_FORWARDED_SCHEME")
    elif "HTTP_X_FORWARDED_PROTO" in environ:
        environ["HTTP_ORIGINAL_X_FORWARDED_PROTO"] = environ["HTTP_X_FORWARDED_PROTO"]
        environ["wsgi.url_scheme"] = environ.pop("HTTP_X_FORWARDED_PROTO")


def _handle_forwarded(environ: Dict[str, str]) -> None:
    environ["HTTP_ORIGINAL_FORWARDED"] = environ["HTTP_FORWARDED"]
    for header in (
        "X_FORWARDED_SERVER",
        "X_FORWARDED_HOST",
        "X_FORWARDED_FOR",
        "X_FORWARDED_SCHEME",
        "X_FORWARDED_PROTO",
    ):
        if "HTTP_" + header in environ:
            environ["HTTP_ORIGINAL_" + header] = environ.pop("HTTP_" + header)
    forwarded = SEP_RE.split(environ.pop("HTTP_FORWARDED"))[0]
    fields = dict(tuple(f.split("=", maxsplit=1)) for f in forwarded.split(";"))  # type: ignore
    if "by" in fields:
        environ["SERVER_NAME"] = fields["by"]
    if "for" in fields:
        environ["REMOTE_ADDR"] = fields["for"]
    if "host" in fields:
        environ["HTTP_ORIGINAL_HOST"] = environ["HTTP_HOST"]
        environ["HTTP_HOST"] = fields["host"]
    if "proto" in fields:
        environ["wsgi.url_scheme"] = fields["proto"]


def filter_factory(*args: Any, **kwargs: Any) -> Callable[..., Any]:
    """Get the filter."""
    return Filter
