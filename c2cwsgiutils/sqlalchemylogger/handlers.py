import logging
import traceback
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import createLogClass, Base
from sqlalchemy.exc import OperationalError, InvalidRequestError
from sqlalchemy_utils import database_exists, create_database
import threading
import time
import queue
from .filters import ContainsExpression, DoesNotContainExpression
from typing import Any, List, Dict


LOG = logging.getLogger(__name__)


class SQLAlchemyHandler(logging.Handler):

    MAX_NB_LOGS = 100
    MAX_TIMEOUT = 1

    def __init__(self,
                 sqlalchemyUrl: Dict[str, str],
                 doesNotContainExpression: str = '',
                 containsExpression: str = '') -> None:
        super().__init__()
        # initialize DB session
        self.engine = create_engine(sqlalchemyUrl['url'])
        self.Log = createLogClass(
                  tablename=sqlalchemyUrl.get('tablename', 'logs'),
                  tableargs=sqlalchemyUrl.get('tableargs', None))  # type: ignore
        Base.metadata.bind = self.engine
        DBSession = sessionmaker(bind=self.engine)
        self.session = DBSession()
        # initialize log queue
        self.log_queue: Any = queue.Queue()
        # initialize a thread to process the logs Asynchronously
        self.condition = threading.Condition()
        self.processor_thread = threading.Thread(target=self._processor, daemon=True)
        self.processor_thread.start()
        # initialize filters
        if doesNotContainExpression:
            self.addFilter(DoesNotContainExpression(doesNotContainExpression))
        if containsExpression:
            self.addFilter(ContainsExpression(containsExpression))

    def _processor(self) -> None:
        LOG.debug('{} : starting processor thread'.format(__name__))
        while True:
            logs = []
            time_since_last = time.monotonic()
            while True:
                with self.condition:
                    self.condition.wait(timeout=self.MAX_TIMEOUT)
                    if not self.log_queue.empty():
                        logs.append(self.log_queue.get())
                        self.log_queue.task_done()
                if len(logs) > 0:
                    # try to reduce the number of INSERT requests to the DB
                    # by writing chunks of self.MAX_NB_LOGS size,
                    # but also do not wait forever before writing stuff (self.MAX_TIMOUT)
                    if ((len(logs) >= self.MAX_NB_LOGS) or
                       (time.monotonic() >= (time_since_last + self.MAX_TIMEOUT))):
                        self._write_logs(logs)
                        break
        LOG.debug('{} : stopping processor thread'.format(__name__))

    def _write_logs(self, logs: List[Any]) -> None:
        try:
            self.session.bulk_save_objects(logs)
            self.session.commit()
        except (OperationalError, InvalidRequestError):
            try:
                self.create_db()
                self.session.rollback()
                self.session.bulk_save_objects(logs)
                self.session.commit()
            except Exception as e:
                # if we really cannot commit the log to DB, do not lock the
                # thread and do not crash the application
                LOG.critical(e)
                pass
        finally:
            self.session.expunge_all()

    def create_db(self) -> None:
        LOG.info('{} : creating new database'.format(__name__))
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
        # FIXME: we should not access directly the private __table_args__
        # variable, but add an accessor method in models.Log class
        if (not isinstance(self.Log.__table_args__, type(None)) and
           self.Log.__table_args__.get('schema', None)):
            if not self.engine.dialect.has_schema(self.engine, self.Log.__table_args__['schema']):
                self.engine.execute(sqlalchemy.schema.CreateSchema(self.Log.__table_args__['schema']))
        Base.metadata.create_all(self.engine)

    def emit(self, record: Any) -> None:
        trace = None
        exc = record.__dict__['exc_info']
        if exc:
            trace = traceback.format_exc()
        log = self.Log(
            logger=record.__dict__['name'],
            level=record.__dict__['levelname'],
            trace=trace,
            msg=record.__dict__['msg'])
        with self.condition:
            # put the log in an asynchronous queue
            self.log_queue.put(log)
            self.condition.notify()
