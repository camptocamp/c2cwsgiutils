from cornice import Service
from typing import Any


def create(name: str, path: str, *args: Any, **kwargs: Any) -> Service:
    """
    Create a cornice service with all the default configuration.
    """
    kwargs['cors_origins'] = ["*"]
    kwargs['cors_max_age'] = 86400
    kwargs['depth'] = 2  # to make venusian find the good frame
    kwargs['http_cache'] = 0  # disable client side and proxy caching
    return Service(name, path, *args, **kwargs)
