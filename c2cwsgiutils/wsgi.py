import os
import logging
from pyramid.paster import get_app
from typing import Optional, Any

from c2cwsgiutils import pyramid_logging


def create_application(configfile: Optional[str]=None) -> Any:
    """
    Create a standard WSGI application with the capabilities to use environment variables in the
    configuration file (use %(ENV_VAR)s place holders)

    :param configfile: The configuration file to use
    :return: The application
    """
    configfile_ = pyramid_logging.init(configfile)
    # Load the logging config without using pyramid to be able to use environment variables in there.
    try:
        return get_app(configfile_, 'main', options=os.environ)
    except Exception:
        logging.getLogger(__name__).exception("Failed starting the application")
        raise
