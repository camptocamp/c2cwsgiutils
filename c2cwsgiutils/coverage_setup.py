import logging
import os
import warnings
from typing import Optional

import pyramid.config

_LOG = logging.getLogger(__name__)


def init() -> None:
    """Initialize the code coverage, for backward compatibility."""
    warnings.warn("init function is deprecated; use includeme instead")
    includeme()


def includeme(config: Optional[pyramid.config.Configurator] = None) -> None:
    """Initialize the code coverage."""
    del config  # unused
    if os.environ.get("COVERAGE", "0") != "1":
        return
    import coverage  # pylint: disable=import-outside-toplevel

    _LOG.warning("Setting up code coverage")
    report_dir = "/tmp/coverage/api"  # nosec
    os.makedirs(report_dir, exist_ok=True)
    cov = coverage.Coverage(
        data_file=os.path.join(report_dir, "coverage"),
        data_suffix=True,
        auto_data=True,
        branch=True,
        source=None,
    )
    cov.start()
