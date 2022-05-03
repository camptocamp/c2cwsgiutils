"""
Used by standalone (non-wsgi) processes to setup all the bits and pieces of c2cwsgiutils that could be useful.

Must be imported at the very beginning of the process' life, before any other module is imported.
"""


import argparse
import warnings
from typing import Any, Callable, Dict, Optional, TypedDict, cast

import pyramid.registry
import pyramid.request
import pyramid.router
import pyramid.config

from pyramid.paster import bootstrap
from pyramid.scripts.common import get_config_loader, parse_vars

from c2cwsgiutils import (
    broadcast,
    coverage_setup,
    redis_stats,
    sentry,
    stats,
    sql_profiler,
)


def fill_arguments(
    parser: argparse.ArgumentParser,
    use_attribute: bool = False,
    default_config_uri: str = "c2c:///app/production.ini",
) -> None:
    """Add the needed arguments to the parser like it's done in pshell."""

    parser.add_argument(
        "--config-uri" if use_attribute else "config_uri",
        nargs="?",
        default=default_config_uri,
        help="The URI to the configuration file.",
    )
    parser.add_argument(
        "--config-vars" if use_attribute else "config_vars",
        nargs="*",
        default=(),
        help="Variables required by the config file. For example, "
        "`http_port=%%(http_port)s` would expect `http_port=8080` to be "
        "passed here.",
    )


def init(config_file: str = "c2c:///app/production.ini") -> None:
    """Initialize the non-WSGI application, for backward compatibility."""
    loader = get_config_loader(config_file)
    loader.setup_logging(None)
    settings = loader.get_settings()
    config = pyramid.config.Configurator(settings=settings)
    coverage_setup.includeme()
    sentry.includeme(config)
    broadcast.includeme(config)
    stats.init_backends(settings)
    redis_stats.includeme(config)
    sql_profiler.includeme(config)


def init_logging(config_file: str = "c2c:///app/production.ini") -> None:
    """Initialize the non-WSGI application."""
    warnings.warn("init_logging function is deprecated; use init instead so that all features are enabled")
    loader = get_config_loader(config_file)
    loader.setup_logging(None)


PyramidEnv = TypedDict(
    "PyramidEnv",
    {
        "root": Any,
        "closer": Callable[..., Any],
        "registry": pyramid.registry.Registry,
        "request": pyramid.request.Request,
        "root_factory": object,
        "app": Callable[[Dict[str, str], Any], Any],
    },
    total=True,
)


def bootstrap_application_from_options(options: argparse.Namespace) -> PyramidEnv:
    """
    Initialize all the application from the command line arguments.

    :return: This function returns a dictionary as in bootstrap, see:
    https://docs.pylonsproject.org/projects/pyramid/en/latest/api/paster.html?highlight=bootstrap#pyramid.paster.bootstrap
    """
    return bootstrap_application(
        options.config_uri, parse_vars(options.config_vars) if options.config_vars else None
    )


def bootstrap_application(
    config_uri: str = "c2c:///app/production.ini",
    options: Optional[Dict[str, Any]] = None,
) -> PyramidEnv:
    """
    Initialize all the application.

    :return: This function returns a dictionary as in bootstrap, see:
    https://docs.pylonsproject.org/projects/pyramid/en/latest/api/paster.html?highlight=bootstrap#pyramid.paster.bootstrap
    """
    loader = get_config_loader(config_uri)
    loader.setup_logging(options)
    return cast(PyramidEnv, bootstrap(config_uri, options=options))
