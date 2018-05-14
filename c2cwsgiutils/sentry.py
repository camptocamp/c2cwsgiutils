import contextlib
import logging
import os
import pyramid.config
from raven import Client, middleware
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging
from typing import MutableMapping, Any, Generator, Optional, Callable  # noqa  # pylint: disable=unused-import

from c2cwsgiutils import _utils

LOG = logging.getLogger(__name__)
client = None


def init(config: Optional[pyramid.config.Configurator]=None) -> None:
    global client
    sentry_url = _utils.env_or_config(config, 'SENTRY_URL', 'c2c.sentry.url')
    if sentry_url is not None:
        if client is None:
            client_info = {
                key[14:].lower(): value
                for key, value in os.environ.items() if key.startswith('SENTRY_CLIENT_')
            }  # type: MutableMapping[str, Any]
            git_hash = _utils.env_or_config(config, 'GIT_HASH', 'c2c.git_hash')
            if git_hash is not None and not ('release' in client_info and client_info['release'] != 'latest'):
                client_info['release'] = git_hash
            client_info['tags'] = {key[11:].lower(): value
                                   for key, value in os.environ.items() if key.startswith('SENTRY_TAG_')}
            client_info['ignore_exceptions'] = client_info.get('ignore_exceptions', 'SystemExit').split(",")
            client = Client(sentry_url, **client_info)
            LOG.info("Configured sentry reporting with client=%s", repr(client_info))
        handler = SentryHandler(client=client)
        handler.setLevel(_utils.env_or_config(config, 'SENTRY_LEVEL', 'c2c.sentry_level', 'ERROR').upper())

        excludes = _utils.env_or_config(config, "SENTRY_EXCLUDES", "c2c.sentry.excludes", "raven").split(",")
        if setup_logging(handler, exclude=excludes):
            LOG.info("Configured sentry logging hook")


@contextlib.contextmanager
def capture_exceptions() -> Generator[None, None, None]:
    """
    Will send exceptions raised withing the context to Sentry.

    You don't need to use that for exception terminating the process (those not catched). Sentry does that
    already.
    """
    global client
    if client is not None:
        try:
            yield
        except Exception:
            client.captureException()
            raise
    else:
        yield


def filter_wsgi_app(application: Callable) -> Callable:
    """
    If sentry is configured, add a Sentry filter around the application
    """
    global client
    if client is not None:
        try:
            LOG.info("Enable WSGI filter for Sentry")
            return middleware.Sentry(application, client)
        except Exception:
            LOG.error("Failed enabling sentry. Continuing without it.", exc_info=True)
            return application
    else:
        return application
