import logging
import os
from tempfile import gettempdir
from typing import Callable

LOG = logging.getLogger(__name__)
_PATH = os.environ.get("C2C_PROFILER_PATH", "")
_MODULES = os.environ.get("C2C_PROFILER_MODULES", "")


def filter_wsgi_app(application: Callable) -> Callable:
    if _PATH != "":
        try:
            import linesman.middleware
            LOG.info("Enable WSGI filter for the profiler on %s", _PATH)
            linesman.middleware.ENABLED_FLAG_FILE = os.path.join(gettempdir(), 'linesman-enabled')
            return linesman.middleware.ProfilingMiddleware(
                app=application, profiler_path=_PATH, chart_packages=_MODULES,
                filename=os.path.join(gettempdir(), 'linesman-graph-sessions.db'))
        except Exception:  # pragma: no cover
            LOG.error("Failed enabling the profiler. Continuing without it.", exc_info=True)
            return application
    else:  # pragma: no cover
        return application
