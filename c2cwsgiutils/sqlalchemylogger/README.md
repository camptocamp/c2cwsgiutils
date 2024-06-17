This module is used to ship logging records to an SQL database.

Currently only `sqlite` and `postgres_psycopg2` are fully supported.

To add the handler, setup it directly in your app's main function. You
can add it to an existing logger (setup in you `.ini` file),
or create a new logger by calling the `logging.getlogger` method.

```python
import logging
from c2cwsgiutils.sqlalchemylogger.handlers import SQLAlchemyHandler

def _setup_sqlalchemy_logger():
    """
    Setup sqlalchemy logger.
    """
    logger = logging.getLogger("A_LOGGER")
    handler = SQLAlchemyHandler(
        sqlalchemy_url={
            # "url": "sqlite:///logger_db.sqlite3",
            "url": "postgresql://postgres:password@localhost:5432/test",
            "tablename": "test",
            "tableargs": {"schema": "xyz"},
        },
        does_not_contain_expression="curl",
    )
    logger.addHandler(handler)

def main(_, **settings):
   _setup_sqlalchemy_logger ()
...
```

Do not set up this sqlalchemy logger in you `.ini` file directly.
It won't work (multi process issue).

if the given credentials are sufficient, the handler will
create the DB, schema and table it needs directly.

In the above example the second parameter provided `'curl'` is a negative
filter (any valid regex will work) to avoid writing the matching logs to the
DB. Useful to filter out health-check specific `User-Agent` headers or so.

To use the handler in a script, you might:

```python
import logging
import time

from c2cwsgiutils.sqlalchemylogger.handlers import SQLAlchemyHandler

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s : %(name)s : %(levelname)s : %(message)s',
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)
    logger_db_engine = {'url':'sqlite:///logger_db.sqlite3'}

    logger.addHandler(SQLAlchemyHandler(logger_db_engine))
    logger.info('bla')
    # wait a few seconds because the second thread will write the
    # logs after a timeout
    time.sleep(2)
```
