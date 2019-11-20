from c2cwsgiutils import (
    broadcast,
    debug,
    errors,
    index,
    logging_view,
    metrics,
    pretty_json,
    redis_stats,
    request_tracking,
    sentry,
    sql_profiler,
    stats_pyramid,
    version,
)
import cornice
import pyramid.config
import pyramid_tm


def includeme(config: pyramid.config.Configurator) -> None:
    """
    Setup all the pyramid services and event handlers provided by this library.

    :param config: The pyramid Configuration
    """
    sentry.init(config)
    config.add_settings(handle_exceptions=False)
    config.include(pyramid_tm.includeme)
    config.include(cornice.includeme)
    pretty_json.init(config)
    broadcast.init(config)
    stats_pyramid.init(config)
    request_tracking.init(config)
    redis_stats.init(config)
    logging_view.install_subscriber(config)
    sql_profiler.init(config)
    version.init(config)
    debug.init(config)
    metrics.init(config)
    errors.init(config)
    index.init(config)
