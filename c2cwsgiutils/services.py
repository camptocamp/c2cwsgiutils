from cornice import Service
from typing import Any


def create(name: str, path: str, *args: Any, **kwargs: Any) -> Service:
    """
    Create a cornice service with all the default configuration.
    """
    kwargs.setdefault('cors_origins', "*")
    kwargs.setdefault('cors_max_age', 86400)
    kwargs.setdefault('depth', 2)  # to make venusian find the good frame
    kwargs.setdefault('http_cache', 0)  # disable client side and proxy caching by default
    kwargs.setdefault('renderer', 'fast_json')
    return Service(name, path, *args, **kwargs)
