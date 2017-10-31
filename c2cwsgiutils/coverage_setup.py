import coverage
import logging
import os

LOG = logging.getLogger(__name__)


def init() -> None:
    """
    Maybe setup code coverage.
    """
    if os.environ.get("COVERAGE", "0") != "1":
        return
    LOG.warning("Setting up code coverage")
    report_dir = "/tmp/coverage/api"
    os.makedirs(report_dir, exist_ok=True)
    cov = coverage.Coverage(data_file=os.path.join(report_dir, 'coverage'), data_suffix=True,
                            auto_data=True, branch=True, source=None)
    cov.start()
