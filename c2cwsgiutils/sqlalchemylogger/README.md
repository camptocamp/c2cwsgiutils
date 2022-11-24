This module is used to ship logging records to an SQL database.

Currently only `sqlite` and `postgres_psycopg2` are fully supported.

To add the logger in a pyramid ini file use something like:

```
[handlers]
keys = sqlalchemy_logger

[handler_sqlalchemy_logger]
class = c2cwsgiutils.sqlalchemylogger.handlers.SQLAlchemyHandler
#args = ({'url':'sqlite:///logger_db.sqlite3','tablename':'test'},'curl')
args = ({'url':'postgresql://postgres:password@localhost:5432/test','tablename':'test','tableargs': {'schema':'xyz'}},'curl')
level = NOTSET
formatter = generic
propagate = 0
```

if the credentials given in `args = ` section are sufficient, the handler will
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
