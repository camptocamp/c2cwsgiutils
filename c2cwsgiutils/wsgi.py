import os
from logging.config import fileConfig
from pyramid.paster import get_app


def create_application(configfile="/app/production.ini"):
    """
    Create a standard WSGI application with the capabilities to use environment variables in the
    configuration file (use %(ENV_VAR)s place holders)
    :param config: The configuration file to use (relative to root)
    :return: The application
    """
    # Load the logging config without using pyramid to be able to use environment variables in there.
    fileConfig(configfile, defaults=os.environ)
    return get_app(configfile, 'main', options=os.environ)
