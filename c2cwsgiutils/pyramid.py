import logging

import cornice
import pyramid.config
import pyramid_tm

from c2cwsgiutils import (
    broadcast,
    coverage_setup,
    db_maintenance_view,
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


def includeme(config: pyramid.config.Configurator) -> None:
    """
    Initialize all the pyramid services and event handlers provided by this library.

    Arguments:

        config: The pyramid Configuration
    """
    logging.captureWarnings(True)
    config.include(coverage_setup.includeme)
    config.include(sentry.includeme)
    config.add_settings(handle_exceptions=False)
    config.include(pyramid_tm.includeme)
    config.include(cornice.includeme)
    config.include(pretty_json.includeme)
    config.include(broadcast.includeme)
    config.include(stats_pyramid.includeme)
    config.include(request_tracking.includeme)
    config.include(redis_stats.includeme)
    config.include(db_maintenance_view.includeme)
    config.include(logging_view.includeme)
    config.include(sql_profiler.includeme)
    config.include(version.includeme)
    config.include(debug.includeme)
    config.include(metrics.includeme)
    config.include(errors.includeme)
    config.include(index.includeme)
