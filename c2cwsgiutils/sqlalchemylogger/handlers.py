import logging
import queue
import threading
import time
import traceback
from typing import Any

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

from c2cwsgiutils.sqlalchemylogger._filters import ContainsExpression, DoesNotContainExpression
from c2cwsgiutils.sqlalchemylogger._models import Base, create_log_class

_LOG = logging.getLogger(__name__)


class SQLAlchemyHandler(logging.Handler):
    """Write the logs into a database."""

    MAX_NB_LOGS = 100
    MAX_TIMEOUT = 1

    def __init__(
        self,
        sqlalchemy_url: dict[str, str],
        does_not_contain_expression: str = "",
        contains_expression: str = "",
    ) -> None:
        super().__init__()
        # Initialize DB session
        self.engine = create_engine(sqlalchemy_url["url"])
        self.Log = create_log_class(  # pylint: disable=invalid-name
            tablename=sqlalchemy_url.get("tablename", "logs"),
            tableargs=sqlalchemy_url.get("tableargs", None),  # type: ignore
        )
        Base.metadata.bind = self.engine
        self.session = sessionmaker(bind=self.engine)()  # noqa
        # Initialize log queue
        self.log_queue: Any = queue.Queue()
        # Initialize a thread to process the logs Asynchronously
        self.condition = threading.Condition()
        self.processor_thread = threading.Thread(target=self._processor, daemon=True)
        self.processor_thread.start()
        # Initialize filters
        if does_not_contain_expression:
            self.addFilter(DoesNotContainExpression(does_not_contain_expression))
        if contains_expression:
            self.addFilter(ContainsExpression(contains_expression))

    def _processor(self) -> None:
        _LOG.debug("%s: starting processor thread", __name__)
        while True:
            logs = []
            time_since_last = time.perf_counter()
            while True:
                with self.condition:
                    self.condition.wait(timeout=self.MAX_TIMEOUT)
                    if not self.log_queue.empty():
                        logs.append(self.log_queue.get())
                        self.log_queue.task_done()
                if logs:
                    # try to reduce the number of INSERT requests to the DB
                    # by writing chunks of self.MAX_NB_LOGS size,
                    # but also do not wait forever before writing stuff (self.MAX_TIMOUT)
                    if (len(logs) >= self.MAX_NB_LOGS) or (
                        time.perf_counter() >= (time_since_last + self.MAX_TIMEOUT)
                    ):
                        self._write_logs(logs)
                        break
        _LOG.debug("%s: stopping processor thread", __name__)

    def _write_logs(self, logs: list[Any]) -> None:
        try:
            self.session.bulk_save_objects(logs)
            self.session.commit()
        except SQLAlchemyError:
            try:
                self.create_db()
                self.session.rollback()
                self.session.bulk_save_objects(logs)
                self.session.commit()
            except Exception as e:  # pylint: disable=broad-except
                # if we really cannot commit the log to DB, do not lock the
                # thread and do not crash the application
                _LOG.critical(e)
        finally:
            self.session.expunge_all()

    def create_db(self) -> None:
        """Create the database if it does not exist."""
        _LOG.info("%s: creating new database", __name__)
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
        # FIXME: we should not access directly the private __table_args__
        # variable, but add an accessor method in models.Log class
        if not isinstance(self.Log.__table_args__, type(None)) and self.Log.__table_args__.get(
            "schema", None
        ):
            with self.engine.begin() as connection:
                if not self.engine.dialect.has_schema(connection, self.Log.__table_args__["schema"]):
                    connection.execute(
                        sqlalchemy.schema.CreateSchema(self.Log.__table_args__["schema"]),
                    )
        Base.metadata.create_all(self.engine)

    def emit(self, record: Any) -> None:
        trace = None
        exc = record.__dict__["exc_info"]
        if exc:
            trace = traceback.format_exc()
        log = self.Log(
            logger=record.__dict__["name"],
            level=record.__dict__["levelname"],
            trace=trace,
            msg=record.__dict__["msg"],
        )
        with self.condition:
            # put the log in an asynchronous queue
            self.log_queue.put(log)
            self.condition.notify()
