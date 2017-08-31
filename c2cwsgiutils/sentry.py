import contextlib
import logging
import os
from raven import Client, middleware
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

from c2cwsgiutils import _utils

LOG = logging.getLogger(__name__)
client = None


def init(config=None):
    global client
    sentry_url = _utils.env_or_config(config, 'SENTRY_URL', 'c2c.sentry.url')
    if sentry_url is not None:  # pragma: no cover
        client_info = {key[14:].lower(): value
                       for key, value in os.environ.items() if key.startswith('SENTRY_CLIENT_')}
        git_hash = _utils.env_or_config(config, 'GIT_HASH', 'c2c.git_hash')
        if git_hash is not None and not ('release' in client_info and client_info['release'] != 'latest'):
            client_info['release'] = git_hash
        client_info['tags'] = {key[11:].lower(): value
                               for key, value in os.environ.items() if key.startswith('SENTRY_TAG_')}
        client_info['ignore_exceptions'] = client_info.get('ignore_exceptions', 'SystemExit').split(",")
        client = Client(sentry_url, **client_info)
        handler = SentryHandler(client=client)
        handler.setLevel(logging.ERROR)

        excludes = _utils.env_or_config(config, "SENTRY_EXCLUDES", "c2c.sentry.excludes", "raven").split(",")
        setup_logging(handler, exclude=excludes)
        LOG.info("Configured sentry reporting with client=%s", repr(client_info))


@contextlib.contextmanager
def capture_exceptions():
    """
    Will send exceptions raised withing the context to Sentry.

    You don't need to use that for exception terminating the process (those not catched). Sentry does that
    already.
    """
    global client
    if client is not None:
        try:
            yield
        except:
            client.captureException()
            raise
    else:
        yield


def filter_wsgi_app(application):  # pragma: no cover
    """
    If sentry is configured, add a Sentry filter around the application
    """
    global client
    if client is not None:
        LOG.info("Enable WSGI filter for Sentry")
        return middleware.Sentry(application, client)
    else:
        return application
