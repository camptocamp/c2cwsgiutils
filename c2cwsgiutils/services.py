import logging
from typing import Any

from cornice import Service
from pyramid.request import Request
from pyramid.response import Response

_LOG = logging.getLogger(__name__)


def create(name: str, path: str, *args: Any, **kwargs: Any) -> Service:
    """Create a cornice service with all the default configuration."""
    kwargs.setdefault("cors_origins", "*")
    kwargs.setdefault("cors_max_age", 86400)
    kwargs.setdefault("depth", 2)  # to make venusian find the good frame
    kwargs.setdefault("http_cache", 0)  # disable client side and proxy caching by default
    kwargs.setdefault("renderer", "cornice_fast_json")
    kwargs.setdefault("filters", []).append(_cache_cors)
    return Service(name, path, *args, **kwargs)


def _cache_cors(response: Response, request: Request) -> Response:
    """Cornice filter that fixes the Cache-Control header for pre-flight requests (OPTIONS)."""
    try:
        if request.method == "OPTIONS" and "Access-Control-Max-Age" in response.headers:
            response.cache_control = {"max-age": int(response.headers["Access-Control-Max-Age"])}
            if response.vary is None:
                response.vary = ["Origin"]
            elif "Origin" not in response.vary:
                response.vary.append("Origin")
    except Exception:
        # cornice catches exceptions from filters, and tries call back the filter with only the request.
        # This leads to a useless message in case of error...
        _LOG.error("Failed fixing cache headers for CORS", exc_info=True)
        raise
    return response
