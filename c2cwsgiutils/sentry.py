import contextlib
import logging
import os
from raven import Client
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

LOG = logging.getLogger(__name__)
client = None


def init():
    global client
    if 'SENTRY_URL' in os.environ:
        client_info = {key[14:].lower(): value
                       for key, value in os.environ.items() if key.startswith('SENTRY_CLIENT_')}
        if 'GIT_HASH' in os.environ and not ('release' in client_info and client_info['release'] != 'latest'):
            client_info['release'] = os.environ['GIT_HASH']
        client_info['tags'] = {key[11:].lower(): value
                               for key, value in os.environ.items() if key.startswith('SENTRY_TAG_')}
        client = Client(os.environ['SENTRY_URL'], **client_info)
        handler = SentryHandler(client=client)
        handler.setLevel(logging.ERROR)

        setup_logging(handler, exclude=('raven', ))
        LOG.info("Configured sentry reporting with client=%s", repr(client_info))


@contextlib.contextmanager
def capture_exceptions():
    global client
    if client is not None:
        try:
            yield
        except:
            client.captureException()
            raise
    else:
        yield
