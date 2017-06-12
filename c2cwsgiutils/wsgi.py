import os
import logging
from logging.config import fileConfig
from pyramid.paster import get_app


def create_application(configfile=None):
    """
    Create a standard WSGI application with the capabilities to use environment variables in the
    configuration file (use %(ENV_VAR)s place holders)

    :param config: The configuration file to use
    :return: The application
    """
    logging.captureWarnings(True)
    if configfile is None:
        configfile = os.environ.get('C2CWSGIUTILS_CONFIG', "/app/production.ini")
    # Load the logging config without using pyramid to be able to use environment variables in there.
    fileConfig(configfile, defaults=os.environ)
    try:
        return get_app(configfile, 'main', options=os.environ)
    except:
        logging.getLogger(__name__).exception("Failed starting the application")
        raise
