import logging
import os
from typing import Any, Mapping, Optional

from pyramid.paster import get_app

from c2cwsgiutils import pyramid_logging


def _escape_variables(environ: Mapping[str, str]) -> Mapping[str, str]:
    """
    Escape environment variables so that they can be interpreted correctly by python configparser.
    """
    return {key: environ[key].replace("%", "%%") for key in environ}


def create_application(configfile: Optional[str] = None) -> Any:
    """
    Create a standard WSGI application with the capabilities to use environment variables in the
    configuration file (use %(ENV_VAR)s place holders)

    :param configfile: The configuration file to use
    :return: The application
    """
    configfile_ = pyramid_logging.init(configfile)
    # Load the logging config without using pyramid to be able to use environment variables in there.
    try:
        options = _escape_variables(os.environ)
        return get_app(configfile_, "main", options=options)
    except Exception:
        logging.getLogger(__name__).exception("Failed starting the application")
        raise
