import cornice
import pyramid_tm

from c2cwsgiutils import stats_pyramid, pyramid_logging, sql_profiler, version, debug


def includeme(config):
    """
    Setup all the pyramid services and event handlers provided by this library.

    :param config: The pyramid Configuration
    """
    config.add_settings(handle_exceptions=False)
    config.include(pyramid_tm.includeme)
    config.include(cornice.includeme)
    stats_pyramid.init(config)
    pyramid_logging.install_subscriber(config)
    sql_profiler.init(config)
    version.init(config)
    debug.init(config)
    config.scan("c2cwsgiutils.errors")
