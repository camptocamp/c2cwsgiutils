import logging
import os
from typing import Callable

LOG = logging.getLogger(__name__)
_PATH = os.environ.get("C2C_PROFILER_PATH", "")
_MODULES = os.environ.get("C2C_PROFILER_MODULES", "")


def filter_wsgi_app(application: Callable) -> Callable:
    if _PATH != "":
        import linesman.middleware
        LOG.info("Enable WSGI filter for the profiler on %s", _PATH)
        return linesman.middleware.ProfilingMiddleware(app=application, profiler_path=_PATH,
                                                       chart_packages=_MODULES)
    else:
        return application
