"""SQLalchemy models."""

import logging
import re
import warnings
from collections.abc import Callable, Iterable
from re import Pattern
from typing import Any, cast

import pyramid.config
import pyramid.config.settings
import pyramid.request
import sqlalchemy.engine
import sqlalchemy.orm
import transaction
import zope.sqlalchemy
from sqlalchemy import engine_from_config
from zope.sqlalchemy import register

_scoped_session = sqlalchemy.orm.scoped_session[sqlalchemy.orm.Session]
_sessionmaker = sqlalchemy.orm.sessionmaker[sqlalchemy.orm.Session]  # pylint: disable=unsubscriptable-object


_LOG = logging.getLogger(__name__)
_RE_COMPILE: Callable[[str], Pattern[str]] = re.compile

FORCE_READONLY = False


class Tweens:
    """The tween base class."""


tweens = Tweens()


def setup_session(
    config: pyramid.config.Configurator,
    master_prefix: str,
    slave_prefix: str | None = None,
    force_master: Iterable[str] | None = None,
    force_slave: Iterable[str] | None = None,
) -> tuple[
    sqlalchemy.orm.Session | _scoped_session,
    sqlalchemy.engine.Engine,
    sqlalchemy.engine.Engine,
]:
    """
    Create a SQLAlchemy session.

    With an accompanying tween that switches between the master and the slave DB
    connection. Uses prefixed entries in the application's settings.

    The slave DB will be used for anything that is GET and OPTIONS queries. The master DB will be used for
    all the other queries. You can tweak this behavior with the force_master and force_slave parameters.
    Those parameters are lists of regex that are going to be matched against "{VERB} {PATH}". Warning, the
    path includes the route_prefix.

    Arguments:
        config: The pyramid Configuration object
        master_prefix: The prefix for the master connection configuration entries in the application \
                          settings
        slave_prefix: The prefix for the slave connection configuration entries in the application \
                         settings
        force_master: The method/paths that needs to use the master
        force_slave: The method/paths that needs to use the slave

    Returns: The SQLAlchemy session, the R/W engine and the R/O engine

    """
    warnings.warn(
        "setup_session function is deprecated; use init and request.dbsession instead",
        stacklevel=2,
    )
    if slave_prefix is None:
        slave_prefix = master_prefix
    settings = config.registry.settings
    rw_engine = sqlalchemy.engine_from_config(settings, master_prefix + ".")
    rw_engine.c2c_name = master_prefix  # type: ignore[attr-defined]
    factory = sqlalchemy.orm.sessionmaker(bind=rw_engine)
    register(factory)
    db_session = sqlalchemy.orm.scoped_session(factory)

    # Setup a slave DB connection and add a tween to use it.
    if settings[master_prefix + ".url"] != settings.get(slave_prefix + ".url"):
        _LOG.info("Using a slave DB for reading %s", master_prefix)
        ro_engine = sqlalchemy.engine_from_config(config.get_settings(), slave_prefix + ".")
        ro_engine.c2c_name = slave_prefix  # type: ignore[attr-defined]
        tween_name = master_prefix.replace(".", "_")
        _add_tween(config, tween_name, db_session, force_master, force_slave)
    else:
        ro_engine = rw_engine

    db_session.c2c_rw_bind = rw_engine  # type: ignore[attr-defined]
    db_session.c2c_ro_bind = ro_engine  # type: ignore[attr-defined]
    return db_session, rw_engine, ro_engine


def create_session(
    config: pyramid.config.Configurator | None,
    name: str,
    url: str,
    slave_url: str | None = None,
    force_master: Iterable[str] | None = None,
    force_slave: Iterable[str] | None = None,
    **engine_config: Any,
) -> sqlalchemy.orm.Session | _scoped_session:
    """
    Create a SQLAlchemy session.

    With an accompanying tween that switches between the master and the slave DB
    connection.

    The slave DB will be used for anything that is GET and OPTIONS queries. The master DB will be used for
    all the other queries. You can tweak this behavior with the force_master and force_slave parameters.
    Those parameters are lists of regex that are going to be matched against "{VERB} {PATH}". Warning, the
    path includes the route_prefix.

    Arguments:
        config: The pyramid Configuration object. If None, only master is used
        name: The name of the check
        url: The URL for the master DB
        slave_url: The URL for the slave DB
        force_master: The method/paths that needs to use the master
        force_slave: The method/paths that needs to use the slave
        engine_config: The rest of the parameters are passed as is to the sqlalchemy.create_engine function

    Returns: The SQLAlchemy session

    """
    warnings.warn(
        "create_session function is deprecated; use init and request.dbsession instead",
        stacklevel=2,
    )
    if slave_url is None:
        slave_url = url

    rw_engine = sqlalchemy.create_engine(url, **engine_config)
    factory = sqlalchemy.orm.sessionmaker(bind=rw_engine)
    register(factory)
    db_session = sqlalchemy.orm.scoped_session(factory)

    # Setup a slave DB connection and add a tween to use it.
    if url != slave_url and config is not None:
        _LOG.info("Using a slave DB for reading %s", name)
        ro_engine = sqlalchemy.create_engine(slave_url, **engine_config)
        _add_tween(config, name, db_session, force_master, force_slave)
        rw_engine.c2c_name = name + "_master"  # type: ignore[attr-defined]
        ro_engine.c2c_name = name + "_slave"  # type: ignore[attr-defined]
    else:
        rw_engine.c2c_name = name  # type: ignore[attr-defined]
        ro_engine = rw_engine

    db_session.c2c_rw_bind = rw_engine  # type: ignore[attr-defined]
    db_session.c2c_ro_bind = ro_engine  # type: ignore[attr-defined]
    return db_session


def _add_tween(
    config: pyramid.config.Configurator,
    name: str,
    db_session: _scoped_session,
    force_master: Iterable[str] | None,
    force_slave: Iterable[str] | None,
) -> None:
    master_paths: Iterable[Pattern[str]] = (
        list(map(_RE_COMPILE, force_master)) if force_master is not None else []
    )
    slave_paths: Iterable[Pattern[str]] = (
        list(map(_RE_COMPILE, force_slave)) if force_slave is not None else []
    )

    def db_chooser_tween_factory(
        handler: Callable[[pyramid.request.Request], Any],
        _registry: Any,
    ) -> Callable[[pyramid.request.Request], Any]:
        """
        Tween factory to route to a slave DB for read-only queries.

        Must be put over the pyramid_tm tween and share_config must have a "slave" engine configured.
        """

        def db_chooser_tween(request: pyramid.request.Request) -> Any:
            session = db_session()
            old = session.bind
            method_path: Any = f"{request.method} {request.path}"
            has_force_master = any(r.match(method_path) for r in master_paths)
            if FORCE_READONLY or (
                not has_force_master
                and (request.method in ("GET", "OPTIONS") or any(r.match(method_path) for r in slave_paths))
            ):
                _LOG.debug(
                    "Using %s database for: %s",
                    db_session.c2c_ro_bind.c2c_name,  # type: ignore[attr-defined]
                    method_path,
                )
                session.bind = db_session.c2c_ro_bind  # type: ignore[attr-defined]
            else:
                _LOG.debug(
                    "Using %s database for: %s",
                    db_session.c2c_rw_bind.c2c_name,  # type: ignore[attr-defined]
                    method_path,
                )
                session.bind = db_session.c2c_rw_bind  # type: ignore[attr-defined]

            try:
                return handler(request)
            finally:
                session.bind = old

        return db_chooser_tween

    setattr(tweens, name, db_chooser_tween_factory)
    config.add_tween("c2cwsgiutils.db.tweens." + name, over="pyramid_tm.tm_tween_factory")


class SessionFactory(_sessionmaker):
    """The custom session factory that manage the read only and read write sessions."""

    def __init__(
        self,
        force_master: Iterable[str] | None,
        force_slave: Iterable[str] | None,
        ro_engine: sqlalchemy.engine.Engine,
        rw_engine: sqlalchemy.engine.Engine,
    ) -> None:
        """Initialize the session factory."""
        super().__init__()
        self.master_paths: Iterable[Pattern[str]] = (
            list(map(_RE_COMPILE, force_master)) if force_master else []
        )
        self.slave_paths: Iterable[Pattern[str]] = list(map(_RE_COMPILE, force_slave)) if force_slave else []
        self.ro_engine = ro_engine
        self.rw_engine = rw_engine

    def engine_name(self, readwrite: bool) -> str:
        """Get the engine name."""
        if readwrite:
            return cast("str", self.rw_engine.c2c_name)  # type: ignore[attr-defined]
        return cast("str", self.ro_engine.c2c_name)  # type: ignore[attr-defined]

    def __call__(  # type: ignore[override]
        self,
        request: pyramid.request.Request | None,
        readwrite: bool | None = None,
        **local_kw: Any,
    ) -> _scoped_session:
        """Set the engine based on the request."""
        if readwrite is not None:
            if readwrite and not FORCE_READONLY:
                _LOG.debug("Using %s database", self.rw_engine.c2c_name)  # type: ignore[attr-defined]
                self.configure(bind=self.rw_engine)
            else:
                _LOG.debug("Using %s database", self.ro_engine.c2c_name)  # type: ignore[attr-defined]
                self.configure(bind=self.ro_engine)
        else:
            assert request is not None
            method_path: str = f"{request.method} {request.path}" if request is not None else ""
            has_force_master = any(r.match(method_path) for r in self.master_paths)
            if FORCE_READONLY or (
                not has_force_master
                and (
                    request.method in ("GET", "OPTIONS")
                    or any(r.match(method_path) for r in self.slave_paths)
                )
            ):
                _LOG.debug("Using %s database for: %s", self.ro_engine.c2c_name, method_path)  # type: ignore[attr-defined]
                self.configure(bind=self.ro_engine)
            else:
                _LOG.debug("Using %s database for: %s", self.rw_engine.c2c_name, method_path)  # type: ignore[attr-defined]
                self.configure(bind=self.rw_engine)
        return super().__call__(**local_kw)  # type: ignore[return-value]


def get_engine(
    settings: pyramid.config.settings.Settings,
    prefix: str = "sqlalchemy.",
) -> sqlalchemy.engine.Engine:
    """Get the engine from the settings."""
    return engine_from_config(settings, prefix)


def get_session_factory(
    engine: sqlalchemy.engine.Engine,
) -> _sessionmaker:
    """Get the session factory from the engine."""
    factory = _sessionmaker()
    factory.configure(bind=engine)
    return factory


def get_tm_session(
    session_factory: _sessionmaker,
    transaction_manager: transaction.TransactionManager,
) -> sqlalchemy.orm.Session:
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    This function will hook the session to the transaction manager which
    will take care of committing any changes.

    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.

    - When using scripts you should wrap the session in a manager yourself.
      For example:

      .. code-block:: python

          import transaction
          import c2cwsgiutils.db

          engine = c2cwsgiutils.db.get_engine(settings)
          session_factory = c2cwsgiutils.db.get_session_factory(engine)
          with transaction.manager:
              dbsession = c2cwsgiutils.db.get_tm_session(session_factory, transaction.manager)

    This function may be invoked with a ``request`` kwarg, such as when invoked
    by the reified ``.dbsession`` Pyramid request attribute which is configured
    via the ``includeme`` function below. The default value, for backwards
    compatibility, is ``None``.

    The ``request`` kwarg is used to populate the ``sqlalchemy.orm.Session``'s
    "info" dict.  The "info" dict is the official namespace for developers to
    stash session-specific information.  For more information, please see the
    SQLAlchemy docs:
    https://docs.sqlalchemy.org/en/stable/orm/session_api.html#sqlalchemy.orm.session.Session.params.info

    By placing the active ``request`` in the "info" dict, developers will be
    able to access the active Pyramid request from an instance of an SQLAlchemy
    object in one of two ways:

    - Classic SQLAlchemy. This uses the ``Session``'s utility class method:

      .. code-block:: python

          from sqlalchemy.orm.session import Session as sa_Session

          dbsession = sa_Session.object_session(dbObject)
          request = dbsession.info["request"]

    - Modern SQLAlchemy. This uses the "Runtime Inspection API":

      .. code-block:: python

          from sqlalchemy import inspect as sa_inspect

          dbsession = sa_inspect(dbObject).session
          request = dbsession.info["request"]
    """
    dbsession = session_factory()
    assert isinstance(dbsession, sqlalchemy.orm.Session), type(dbsession)
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    return dbsession


def get_tm_session_pyramid(
    session_factory: SessionFactory,
    transaction_manager: transaction.TransactionManager,
    request: pyramid.request.Request,
) -> _scoped_session:
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    Same as ``get_tm_session`` to be used in a pyramid request.
    """
    dbsession = session_factory(request=request)
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    return dbsession


def init(
    config: pyramid.config.Configurator,
    master_prefix: str,
    slave_prefix: str | None = None,
    force_master: Iterable[str] | None = None,
    force_slave: Iterable[str] | None = None,
) -> SessionFactory:
    """
    Initialize the database for a Pyramid app.

    Arguments:
        config: The pyramid Configuration object
        master_prefix: The prefix for the master connection configuration entries in the application \
                          settings
        slave_prefix: The prefix for the slave connection configuration entries in the application \
                         settings
        force_master: The method/paths that needs to use the master
        force_slave: The method/paths that needs to use the slave

    Returns: The SQLAlchemy session

    """
    settings = config.get_settings()
    settings["tm.manager_hook"] = "pyramid_tm.explicit_manager"

    # hook to share the dbengine fixture in testing
    dbengine = settings.get("dbengine")
    if not dbengine:
        rw_engine = get_engine(settings, master_prefix + ".")
        rw_engine.c2c_name = master_prefix  # type: ignore[attr-defined]

        # Setup a slave DB connection and add a tween to use it.
        if slave_prefix and settings[master_prefix + ".url"] != settings.get(slave_prefix + ".url"):
            _LOG.info("Using a slave DB for reading %s", master_prefix)
            ro_engine = get_engine(config.get_settings(), slave_prefix + ".")
            ro_engine.c2c_name = slave_prefix  # type: ignore[attr-defined]
        else:
            ro_engine = rw_engine
    else:
        ro_engine = rw_engine = dbengine

    session_factory = SessionFactory(force_master, force_slave, ro_engine, rw_engine)
    config.registry["dbsession_factory"] = session_factory

    # make request.dbsession available for use in Pyramid
    def dbsession(request: pyramid.request.Request) -> sqlalchemy.orm.Session:
        # hook to share the dbsession fixture in testing
        dbsession = request.environ.get("app.dbsession")
        if dbsession is None:
            # request.tm is the transaction manager used by pyramid_tm
            dbsession = get_tm_session_pyramid(session_factory, request.tm, request=request)
            assert dbsession is not None
        assert isinstance(dbsession, sqlalchemy.orm.Session), type(dbsession)
        return dbsession

    config.add_request_method(dbsession, reify=True)
    return session_factory
