import argparse

import transaction
from c2cwsgiutils_app import models

import c2cwsgiutils.db
import c2cwsgiutils.setup_process


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
        hello = dbsession.query(models.Hello).first()
        print(hello.value)


if __name__ == "__main__":
    main()
