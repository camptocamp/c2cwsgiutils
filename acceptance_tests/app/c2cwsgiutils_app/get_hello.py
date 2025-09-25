import argparse

import psycopg2
import transaction

import c2cwsgiutils.db
import c2cwsgiutils.setup_process

from c2cwsgiutils_app import models


def _fill_db():
    for db, value in (("db", "master"), ("db_slave", "slave")):
        connection = psycopg2.connect(
            database="test", user="www-data", password="www-data", host=db, port=5432
        )
        with connection.cursor() as curs:
            curs.execute("DELETE FROM hello")
            curs.execute("INSERT INTO hello (value) VALUES (%s)", (value,))
        connection.commit()


def main() -> None:
    """Get the fist hello value."""

    parser = argparse.ArgumentParser(description="Get the first hello value.")
    c2cwsgiutils.setup_process.fill_arguments(parser)
    args = parser.parse_args()
    env = c2cwsgiutils.setup_process.bootstrap_application_from_options(args)

    engine = c2cwsgiutils.db.get_engine(env["registry"].settings)
    session_factory = c2cwsgiutils.db.get_session_factory(engine)
    with transaction.manager:
        dbsession = c2cwsgiutils.db.get_tm_session(session_factory, transaction.manager)
        if len(dbsession.query(models.Hello).all()) == 0:
            _fill_db()
        hello = dbsession.query(models.Hello).first()
        print(hello.value)


if __name__ == "__main__":
    main()
