import logging
import time

from c2cwsgiutils.sqlalchemylogger.handlers import SQLAlchemyHandler

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s : %(name)s : %(levelname)s : %(message)s",
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)
    logger_db_engine = {"url": "sqlite:///logger_db.sqlite3"}
    logger.addHandler(SQLAlchemyHandler(logger_db_engine))
    logger.info("bla")
    time.sleep(10)
