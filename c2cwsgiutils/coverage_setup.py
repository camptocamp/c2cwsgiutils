import coverage
import logging
import os
import signal

LOG = logging.getLogger(__name__)


def init():
    """
    Maybe setup code coverage.
    """
    if os.environ.get("COVERAGE", "0") != "1":
        return
    LOG.warning("Setting up code coverage")
    signal.signal(signal.SIGINT, signal_handler)
    report_dir = "/tmp/coverage/api"
    os.makedirs(report_dir, exist_ok=True)
    cov = coverage.Coverage(data_file=os.path.join(report_dir, 'coverage'), data_suffix=True,
                            auto_data=True, branch=True, source=None)
    cov.start()


def signal_handler(signal, frame):
    LOG.info("Caught signal, exiting...")
    exit(42)
