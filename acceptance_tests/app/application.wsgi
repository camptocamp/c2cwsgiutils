import os
from logging.config import fileConfig
from pyramid.paster import get_app

root = "/app"

configfile = os.path.join(root, "production.ini")

# Load the logging config without using pyramid to be able to use environment variables in there.
fileConfig(configfile, defaults=os.environ)

application = get_app(configfile, 'main', options=os.environ)

