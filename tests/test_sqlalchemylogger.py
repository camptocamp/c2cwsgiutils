import logging
import time
import unittest
from pathlib import Path

from sqlalchemy import text

from c2cwsgiutils.sqlalchemylogger.handlers import SQLAlchemyHandler


class SqlAlchemyLoggerTests(unittest.TestCase):
    dummy_db_name = "dummy.db"

    def setUp(self):
        pass

    def tearDown(self):
        if Path(self.dummy_db_name).exists():
            Path(self.dummy_db_name).unlink()

    def test_sqlalchemylogger_handlers(self):
        logger_db_engine = {"url": f"sqlite:///{self.dummy_db_name}"}
        handler = SQLAlchemyHandler(logger_db_engine)
        test_message = "bla this is a test"
        x = logging.LogRecord(
            name="should_pass",
            level=logging.DEBUG,
            pathname="bla",
            lineno=21,
            msg=test_message,
            args=None,
            exc_info=None,
        )
        handler.emit(x)
        time.sleep(handler.MAX_TIMEOUT + 1.0)
        result = handler.session.execute(text("SELECT * FROM logs")).fetchall()
        assert Path(self.dummy_db_name).exists()
        assert test_message == result[0][4]
        assert test_message == result[0][4]
