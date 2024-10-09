import logging
import time
from typing import Any, Callable

import pytest
import requests

_LOG = logging.getLogger(__name__)
_DEFAULT_TIMEOUT = 60


def wait_url(url: str, timeout: float = _DEFAULT_TIMEOUT) -> None:
    """Wait the the URL is available without any error."""

    def what() -> bool:
        _LOG.info("Trying to connect to %s... ", url)
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            _LOG.info("%s service started", url)
            return True
        else:
            return False

    retry_timeout(what, timeout=timeout)


def retry_timeout(what: Callable[[], Any], timeout: float = _DEFAULT_TIMEOUT, interval: float = 0.5) -> Any:
    """
    Retry the function until the timeout.

    Arguments:
        what: the function to try
        timeout: the timeout to get a success
        interval: the interval between try
    """
    timeout = time.perf_counter() + timeout
    while True:
        error = ""
        try:
            ret = what()
            if ret:
                return ret
        except NameError:
            raise
        except Exception as e:  # pylint: disable=broad-except
            error = str(e)
            _LOG.info("  Failed: %s", e)
        if time.perf_counter() > timeout:
            assert False, "Timeout: " + error
        time.sleep(interval)


def approx(struct: Any, **kwargs: Any) -> Any:
    """
    Make float values in deep structures approximative.

    See pytest.approx
    """
    import boltons.iterutils  # pylint: disable=import-outside-toplevel

    if isinstance(struct, float):
        return pytest.approx(struct, **kwargs)

    def visit(_path: list[str], key: Any, value: Any) -> tuple[Any, Any]:
        if isinstance(value, float):
            value = pytest.approx(value, **kwargs)
        return key, value

    return boltons.iterutils.remap(struct, visit)
