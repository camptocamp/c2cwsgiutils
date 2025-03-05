import logging
import time
import typing
from functools import wraps

_LOG = logging.getLogger(__name__)


def retry(
    exception_to_check: typing.Any,
    tries: float = 3,
    delay: float = 0.5,
    backoff: float = 2,
) -> typing.Callable[..., typing.Any]:
    """
    Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    Arguments:
        exception_to_check: the exception to check. may be a tuple of exceptions to check
        tries: number of times to try (not retry) before giving up
        delay: initial delay between retries in seconds
        backoff: backoff multiplier e.g. value of 2 will double the delay each retry

    """

    def deco_retry(f: typing.Callable[..., typing.Any]) -> typing.Callable[..., typing.Any]:
        @wraps(f)
        def f_retry(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check as e:
                    msg = f"{e:s}, Retrying in {mdelay:d} seconds..."
                    _LOG.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry
