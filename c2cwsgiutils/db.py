"""
SQLalchemy models.
"""
import logging
import re
from typing import Pattern  # noqa  # pylint: disable=unused-import
from typing import Any, Callable, Iterable, Optional, Tuple, Union

import pyramid.config
import pyramid.request
import sqlalchemy.orm
from zope.sqlalchemy import register

LOG = logging.getLogger(__name__)
RE_COMPILE: Callable[[str], Pattern[str]] = re.compile

force_readonly = False


class Tweens:
    pass


tweens = Tweens()


def setup_session(
    config: pyramid.config.Configurator,
    master_prefix: str,
    slave_prefix: Optional[str] = None,
    force_master: Optional[Iterable[str]] = None,
    force_slave: Optional[Iterable[str]] = None,
) -> Tuple[
    Union[sqlalchemy.orm.Session, sqlalchemy.orm.scoped_session],
    sqlalchemy.engine.Engine,
    sqlalchemy.engine.Engine,
]:
    """
    Create a SQLAlchemy session with an accompanying tween that switches between the master and the slave
    DB connection. Uses prefixed entries in the application's settings.

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
    if slave_prefix is None:
        slave_prefix = master_prefix
    settings = config.registry.settings
    rw_engine = sqlalchemy.engine_from_config(settings, master_prefix + ".")
    rw_engine.c2c_name = master_prefix
    factory = sqlalchemy.orm.sessionmaker(bind=rw_engine)
    register(factory)
    db_session = sqlalchemy.orm.scoped_session(factory)

    # Setup a slave DB connection and add a tween to use it.
    if settings[master_prefix + ".url"] != settings.get(slave_prefix + ".url"):
        LOG.info("Using a slave DB for reading %s", master_prefix)
        ro_engine = sqlalchemy.engine_from_config(config.get_settings(), slave_prefix + ".")
        ro_engine.c2c_name = slave_prefix
        tween_name = master_prefix.replace(".", "_")
        _add_tween(config, tween_name, db_session, force_master, force_slave)
    else:
        ro_engine = rw_engine

    db_session.c2c_rw_bind = rw_engine
    db_session.c2c_ro_bind = ro_engine
    return db_session, rw_engine, ro_engine


def create_session(
    config: Optional[pyramid.config.Configurator],
    name: str,
    url: str,
    slave_url: Optional[str] = None,
    force_master: Optional[Iterable[str]] = None,
    force_slave: Optional[Iterable[str]] = None,
    **engine_config: Any,
) -> Union[sqlalchemy.orm.Session, sqlalchemy.orm.scoped_session]:
    """
    Create a SQLAlchemy session with an accompanying tween that switches between the master and the slave
    DB connection.

    The slave DB will be used for anything that is GET and OPTIONS queries. The master DB will be used for
    all the other queries. You can tweak this behavior with the force_master and force_slave parameters.
    Those parameters are lists of regex that are going to be matched against "{VERB} {PATH}". Warning, the
    path includes the route_prefix.

    :param config: The pyramid Configuration object. If None, only master is used
    :param name: The name of the check
    :param url: The URL for the master DB
    :param slave_url: The URL for the slave DB
    :param force_master: The method/paths that needs to use the master
    :param force_slave: The method/paths that needs to use the slave
    :param engine_config: The rest of the parameters are passed as is to the sqlalchemy.create_engine function
    :return: The SQLAlchemy session
    """
    if slave_url is None:
        slave_url = url

    rw_engine = sqlalchemy.create_engine(url, **engine_config)
    factory = sqlalchemy.orm.sessionmaker(bind=rw_engine)
    register(factory)
    db_session = sqlalchemy.orm.scoped_session(factory)

    # Setup a slave DB connection and add a tween to use it.
    if url != slave_url and config is not None:
        LOG.info("Using a slave DB for reading %s", name)
        ro_engine = sqlalchemy.create_engine(slave_url, **engine_config)
        _add_tween(config, name, db_session, force_master, force_slave)
        rw_engine.c2c_name = name + "_master"
        ro_engine.c2c_name = name + "_slave"
    else:
        rw_engine.c2c_name = name
        ro_engine = rw_engine

    db_session.c2c_rw_bind = rw_engine
    db_session.c2c_ro_bind = ro_engine
    return db_session


def _add_tween(
    config: pyramid.config.Configurator,
    name: str,
    db_session: Union[sqlalchemy.orm.Session, sqlalchemy.orm.scoped_session],
    force_master: Optional[Iterable[str]],
    force_slave: Optional[Iterable[str]],
) -> None:
    global tweens

    master_paths: Iterable[Pattern[str]] = (
        list(map(RE_COMPILE, force_master)) if force_master is not None else []
    )
    slave_paths: Iterable[Pattern[str]] = (
        list(map(RE_COMPILE, force_slave)) if force_slave is not None else []
    )

    def db_chooser_tween_factory(
        handler: Callable[[pyramid.request.Request], Any], _registry: Any
    ) -> Callable[[pyramid.request.Request], Any]:
        """
        Tween factory to route to a slave DB for read-only queries.
        Must be put over the pyramid_tm tween and share_config must have a "slave" engine
        configured.
        """

        def db_chooser_tween(request: pyramid.request.Request) -> Any:
            session = db_session()
            old = session.bind
            method_path: Any = "%s %s" % (request.method, request.path)
            has_force_master = any(r.match(method_path) for r in master_paths)
            if force_readonly or (
                not has_force_master
                and (request.method in ("GET", "OPTIONS") or any(r.match(method_path) for r in slave_paths))
            ):
                LOG.debug("Using %s database for: %s", db_session.c2c_ro_bind.c2c_name, method_path)
                session.bind = db_session.c2c_ro_bind
            else:
                LOG.debug("Using %s database for: %s", db_session.c2c_rw_bind.c2c_name, method_path)
                session.bind = db_session.c2c_rw_bind

            try:
                return handler(request)
            finally:
                session.bind = old

        return db_chooser_tween

    tweens.__setattr__(name, db_chooser_tween_factory)
    config.add_tween("c2cwsgiutils.db.tweens." + name, over="pyramid_tm.tm_tween_factory")
