import cornice
import pyramid_tm

from c2cwsgiutils import stats_pyramid, logging_view, sql_profiler, version, debug, sentry,\
    request_tracking, errors, pretty_json, _broadcast


def includeme(config):
    """
    Setup all the pyramid services and event handlers provided by this library.

    :param config: The pyramid Configuration
    """
    sentry.init(config)
    config.add_settings(handle_exceptions=False)
    config.include(pyramid_tm.includeme)
    config.include(cornice.includeme)
    pretty_json.init(config)
    _broadcast.init(config)
    stats_pyramid.init(config)
    request_tracking.init(config)
    logging_view.install_subscriber(config)
    sql_profiler.init(config)
    version.init(config)
    debug.init(config)
    errors.init(config)
