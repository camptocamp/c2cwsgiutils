import os
import logging
from logging.config import fileConfig
from pyramid.paster import get_app
from typing import Optional, Any


def create_application(configfile: Optional[str]=None) -> Any:
    """
    Create a standard WSGI application with the capabilities to use environment variables in the
    configuration file (use %(ENV_VAR)s place holders)

    :param configfile: The configuration file to use
    :return: The application
    """
    logging.captureWarnings(True)
    configfile_ = configfile if configfile is not None else \
        os.environ.get('C2CWSGIUTILS_CONFIG', "/app/production.ini")
    # Load the logging config without using pyramid to be able to use environment variables in there.
    fileConfig(configfile_, defaults=dict(os.environ))
    try:
        return get_app(configfile_, 'main', options=os.environ)
    except Exception:
        logging.getLogger(__name__).exception("Failed starting the application")
        raise
