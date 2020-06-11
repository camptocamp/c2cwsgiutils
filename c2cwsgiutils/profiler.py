import logging
import os
from tempfile import gettempdir
from typing import Any, Callable

LOG = logging.getLogger(__name__)
PATH = os.environ.get("C2C_PROFILER_PATH", "")
_MODULES = os.environ.get("C2C_PROFILER_MODULES", "")


def filter_wsgi_app(application: Callable[..., Any]) -> Callable[..., Any]:
    if PATH != "":
        try:
            import linesman.middleware

            LOG.info("Enable WSGI filter for the profiler on %s", PATH)
            linesman.middleware.ENABLED_FLAG_FILE = os.path.join(gettempdir(), "linesman-enabled")
            return linesman.middleware.ProfilingMiddleware(  # type: ignore
                app=application,
                profiler_path=PATH,
                chart_packages=_MODULES,
                filename=os.path.join(gettempdir(), "linesman-graph-sessions.db"),
            )
        except ModuleNotFoundError:
            LOG.error("'linesman' not installer. Continuing without profiler.")
            return application
        except Exception:  # pragma: no cover  # pylint: disable=broad-except
            LOG.error("Failed enabling the profiler. Continuing without it.", exc_info=True)
            return application
    else:  # pragma: no cover
        return application
