"""
SQLalchemy models.
"""
import logging
import re
import sqlalchemy.orm
from zope.sqlalchemy import ZopeTransactionExtension

LOG = logging.getLogger(__name__)


class Tweens(object):
    pass


tweens = Tweens()


def setup_session(config, master_prefix, slave_prefix=None, force_master=None, force_slave=None):
    """
    Create a SQLAlchemy session with an accompanying tween that switches between the master and the slave
    DB connection.

    The slave DB will be used for anything that is GET and OPTIONS queries. The master DB will be used for
    all the other queries. You can tweak this behavior with the force_master and force_slave parameters.
    Those parameters are lists of regex that are going to be matched against "{VERB} {PATH}". Warning, the
    path includes the route_prefix.

    :param config: The pyramid Configuration object
    :param master_prefix: The prefix for the master connection configuration entries in the application \
                          settings
    :param slave_prefix: The prefix for the slave connection configuration entries in the application \
                         settings
    :param force_master: The method/paths that needs to use the master
    :param force_slave: The method/paths that needs to use the slave
    :return: The SQLAlchemy session, the R/W engine and the R/O engine
    """
    def db_chooser_tween_factory(handler, registry):
        """
        Tween factory to route to a slave DB for read-only queries.
        Must be put over the pyramid_tm tween and share_config must have a "slave" engine
        configured.
        """
        master_paths = list(map(re.compile, force_master)) if force_master else []
        slave_paths = list(map(re.compile, force_slave)) if force_slave else []

        def db_chooser_tween(request):
            session = db_session()
            old = session.bind
            method_path = "%s %s" % (request.method, request.path)
            has_force_master = any(r.match(method_path) for r in master_paths)
            if not has_force_master and (request.method in ("GET", "OPTIONS") or
                                         any(r.match(method_path) for r in slave_paths)):
                LOG.debug("Using %s database for: %s", slave_prefix, method_path)
                session.bind = ro_engine
            else:
                LOG.debug("Using %s database for: %s", master_prefix, method_path)
                session.bind = rw_engine

            try:
                return handler(request)
            finally:
                session.bind = old

        return db_chooser_tween

    if slave_prefix is None:
        slave_prefix = master_prefix
    settings = config.registry.settings
    rw_engine = sqlalchemy.engine_from_config(settings, master_prefix + ".")

    # Setup a slave DB connection and add a tween to use it.
    if settings[master_prefix + ".url"] != settings.get(slave_prefix + ".url"):
        LOG.info("Using a slave DB for reading")
        ro_engine = sqlalchemy.engine_from_config(config.get_settings(), slave_prefix + ".")
        tween_name = master_prefix.replace('.', '_')
        tweens.__setattr__(tween_name, db_chooser_tween_factory)
        config.add_tween('c2cwsgiutils.db.tweens.' + tween_name, over="pyramid_tm.tm_tween_factory")
    else:
        ro_engine = rw_engine

    db_session = sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.sessionmaker(extension=ZopeTransactionExtension(), bind=rw_engine))
    db_session.c2c_rw_bind = rw_engine
    db_session.c2c_ro_bind = ro_engine
    rw_engine.c2c_name = master_prefix
    ro_engine.c2c_name = slave_prefix
    return db_session, rw_engine, ro_engine
