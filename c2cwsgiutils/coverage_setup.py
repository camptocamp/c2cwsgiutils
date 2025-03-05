import logging
import os
import warnings
from pathlib import Path

import pyramid.config

_LOG = logging.getLogger(__name__)


def init() -> None:
    """Initialize the code coverage, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead", stacklevel=2)
    includeme()


def includeme(config: pyramid.config.Configurator | None = None) -> None:
    """Initialize the code coverage."""
    del config  # unused
    if os.environ.get("COVERAGE", "0") != "1":
        return
    import coverage  # pylint: disable=import-outside-toplevel

    _LOG.warning("Setting up code coverage")
    report_dir = Path("/tmp/coverage/api")  # noqa: S108 # nosec
    report_dir.mkdir(parents=True, exist_ok=True)
    cov = coverage.Coverage(
        data_file=str(report_dir / "coverage"),
        data_suffix=True,
        auto_data=True,
        branch=True,
        source=None,
    )
    cov.start()
