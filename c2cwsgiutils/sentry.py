import contextlib
import logging
import os
from typing import Any, Callable, Generator, MutableMapping, Optional  # noqa  # pylint: disable=unused-import

import pyramid.config
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger
from sentry_sdk.integrations.pyramid import PyramidIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

from c2cwsgiutils import config_utils

LOG = logging.getLogger(__name__)
_client_setup = False


def _create_before_send_filter(tags: MutableMapping[str, str]) -> Callable[[Any, Any], Any]:
    """
    A filter that adds tags to every events.
    """

    def do_filter(event: Any, hint: Any) -> Any:
        event.setdefault("tags", {}).update(tags)
        return event

    return do_filter


def init(config: Optional[pyramid.config.Configurator] = None) -> None:
    global _client_setup
    sentry_url = config_utils.env_or_config(config, "SENTRY_URL", "c2c.sentry.url")
    if sentry_url is not None and not _client_setup:
        client_info: MutableMapping[str, Any] = {
            key[14:].lower(): value for key, value in os.environ.items() if key.startswith("SENTRY_CLIENT_")
        }
        # Parse bool
        for key in (
            "with_locals",
            "default_integrations",
            "send_default_pii",
            "debug",
            "attach_stacktrace",
            "propagate_traces",
            "auto_enabling_integrations",
            "auto_session_tracking",
        ):
            if key in client_info:
                client_info[key] = client_info[key].lower() in ("1", "t", "true")
        # Parse int
        for key in ("max_breadcrumbs", "shutdown_timeout", "transport_queue_size"):
            if key in client_info:
                client_info[key] = int(client_info[key])
        # Parse float
        for key in ("sample_rate", "traces_sample_rate"):
            if key in client_info:
                client_info[key] = float(client_info[key])

        git_hash = config_utils.env_or_config(config, "GIT_HASH", "c2c.git_hash")
        if git_hash is not None and not ("release" in client_info and client_info["release"] != "latest"):
            client_info["release"] = git_hash
        client_info["ignore_errors"] = client_info.pop("ignore_exceptions", "SystemExit").split(",")
        tags = {key[11:].lower(): value for key, value in os.environ.items() if key.startswith("SENTRY_TAG_")}

        sentry_logging = LoggingIntegration(
            level=logging.DEBUG,
            event_level=config_utils.env_or_config(
                config, "SENTRY_LEVEL", "c2c.sentry_level", "ERROR"
            ).upper(),
        )
        traces_sample_rate = float(
            config_utils.env_or_config(
                config, "SENTRY_TRACES_SAMPLE_RATE", "c2c.sentry_traces_sample_rate", "0.0"
            )
        )
        sentry_sdk.init(
            dsn=sentry_url,
            integrations=[sentry_logging, PyramidIntegration(), SqlalchemyIntegration(), RedisIntegration()],
            traces_sample_rate=traces_sample_rate,
            before_send=_create_before_send_filter(tags),
            **client_info,
        )
        _client_setup = True

        excludes = config_utils.env_or_config(
            config, "SENTRY_EXCLUDES", "c2c.sentry.excludes", "sentry_sdk"
        ).split(",")
        for exclude in excludes:
            ignore_logger(exclude)

        LOG.info("Configured sentry reporting with client=%s and tags=%s", repr(client_info), repr(tags))


@contextlib.contextmanager
def capture_exceptions() -> Generator[None, None, None]:
    """
    Will send exceptions raised within the context to Sentry.

    You don't need to use that for exception terminating the process (those not caught). Sentry does that
    already.
    """
    if _client_setup:
        try:
            yield
        except Exception:
            sentry_sdk.capture_exception()
            raise
    else:
        yield


def filter_wsgi_app(application: Callable[..., Any]) -> Callable[..., Any]:
    """
    If sentry is configured, add a Sentry filter around the application.
    """
    if _client_setup:
        try:
            LOG.info("Enable WSGI filter for Sentry")
            return SentryWsgiMiddleware(application)
        except Exception:  # pylint: disable=broad-except
            LOG.error("Failed enabling sentry. Continuing without it.", exc_info=True)
            return application
    else:
        return application
