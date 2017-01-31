import cornice
import pyramid_tm

from c2cwsgiutils import stats, pyramid_logging


def includeme(config):
    config.include(pyramid_tm.includeme)
    config.include(cornice.includeme)
    stats.init(config)
    pyramid_logging.install_subscriber(config)
    config.scan("c2cwsgiutils.services")
    config.scan("c2cwsgiutils.errors")
