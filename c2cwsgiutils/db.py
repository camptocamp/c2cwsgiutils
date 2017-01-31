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


def setup_session(config, master_prefix, slave_prefix):
    def db_chooser_tween_factory(handler, registry):
        """
        Tween factory to route to a slave DB for read-only queries.
        Must be put over the pyramid_tm tween and share_config must have a "slave" engine
        configured.
        """
        chooser_settings = registry.settings.get("db_chooser", {})
        master_paths = [re.compile(i.replace("//", "/")) for i in chooser_settings.get("master", [])]
        slave_paths = [re.compile(i.replace("//", "/")) for i in chooser_settings.get("slave", [])]

        def db_chooser_tween(request):
            session = db_session()
            old = session.bind
            method_path = "%s %s" % (request.method, request.path)
            force_master = any(r.match(method_path) for r in master_paths)
            if not force_master and (request.method in ("GET", "OPTIONS") or
                                     any(r.match(method_path) for r in slave_paths)):
                LOG.debug("Using slave database for: %s", method_path)
                session.bind = ro_engine
            else:
                LOG.debug("Using master database for: %s", method_path)
                session.bind = rw_engine

            try:
                return handler(request)
            finally:
                session.bind = old

        return db_chooser_tween

    settings = config.registry.settings
    rw_engine = sqlalchemy.engine_from_config(settings, master_prefix + ".")

    # Setup a replica DB connection and add a tween to use it.
    if settings[master_prefix + ".url"] != settings[slave_prefix + ".url"]:
        LOG.info("Using a slave DB for reading")
        ro_engine = sqlalchemy.engine_from_config(config.get_settings(), slave_prefix + ".")
        tweens.__setattr__(master_prefix, db_chooser_tween_factory)
        config.add_tween('c2cwsgiutils.db.tweens.' + master_prefix, over="pyramid_tm.tm_tween_factory")
    else:
        ro_engine = rw_engine

    db_session = sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.sessionmaker(extension=ZopeTransactionExtension(), bind=rw_engine))
    return db_session
