import glob
import logging
import os
import time
import unittest

from c2cwsgiutils.sqlalchemylogger.handlers import SQLAlchemyHandler
from sqlalchemy import text


class SqlAlchemyLoggerTests(unittest.TestCase):
    dummy_db_name = "dummy.db"

    def setUp(self):
        pass

    def tearDown(self):
        if glob.glob(self.dummy_db_name):
            os.remove(self.dummy_db_name)

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
        assert glob.glob(self.dummy_db_name)
        assert test_message == result[0][4]
