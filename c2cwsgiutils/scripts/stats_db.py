#!/usr/bin/env python3
"""Provide prometheus gauges for every tables of a database."""

import argparse
import logging
import os
import sys
import time
from typing import TYPE_CHECKING, Optional
from wsgiref.simple_server import make_server

import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm
import transaction
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client.exposition import make_wsgi_app
from zope.sqlalchemy import register

import c2cwsgiutils.setup_process
from c2cwsgiutils import prometheus

if TYPE_CHECKING:
    scoped_session = sqlalchemy.orm.scoped_session[sqlalchemy.orm.Session]
else:
    scoped_session = sqlalchemy.orm.scoped_session

LOG = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    c2cwsgiutils.setup_process.fill_arguments(parser)
    parser.add_argument("--db", type=str, required=True, help="DB connection string")
    parser.add_argument(
        "--schema", type=str, action="append", required=True, default=["public"], help="schema to dump"
    )
    parser.add_argument(
        "--extra",
        type=str,
        action="append",
        help="A SQL query that returns a metric name and a value",
    )
    parser.add_argument(
        "--extra-gauge",
        type=str,
        action="append",
        nargs=3,
        help="A SQL query that returns a metric name and a value, with gauge name and help",
    )
    parser.add_argument(
        "--prometheus-url", "--prometheus_url", type=str, help="Base URL for the Prometheus Pushgateway"
    )
    parser.add_argument(
        "--prometheus-instance",
        "--prometheus_instance",
        type=str,
        help="Instance name for the Prometheus Pushgateway",
    )

    return parser.parse_args()


class Reporter:
    """The stats reporter."""

    def __init__(self, args: argparse.Namespace) -> None:
        self._error: Optional[Exception] = None
        self.registry = CollectorRegistry()
        self.prometheus_push = args.prometheus_url is not None
        self.args = args
        self.gauges: dict[str, Gauge] = {}

    def get_gauge(self, kind: str, kind_help: str, labels: list[str]) -> Gauge:
        if kind not in self.gauges:
            self.gauges[kind] = Gauge(
                prometheus.build_metric_name(f"database_{kind}"),
                kind_help,
                labels,
                registry=self.registry,
            )
        return self.gauges[kind]

    def do_report(
        self, metric: list[str], value: int, kind: str, kind_help: str, tags: dict[str, str]
    ) -> None:
        LOG.debug("%s.%s -> %d", kind, ".".join(metric), value)
        gauge = self.get_gauge(kind, kind_help, list(tags.keys()))
        gauge.labels(**tags).set(value)

    def commit(self) -> None:
        if self.prometheus_push:
            push_to_gateway(self.args.prometheus_url, job="db_counts", registry=self.registry)
        else:
            port = int(os.environ.get("C2C_PROMETHEUS_PORT", "9090"))
            app = make_wsgi_app(self.registry)
            with make_server("", port, app) as httpd:
                LOG.info("Waiting that Prometheus get the metrics served on port %s...", port)
                httpd.handle_request()

    def error(self, metric: list[str], error_: Exception) -> None:
        if self._error is None:
            self._error = error_

    def report_error(self) -> None:
        if self._error is not None:
            raise self._error


def do_table(
    session: scoped_session,
    schema: str,
    table: str,
    reporter: Reporter,
) -> None:
    """Do the stats on a table."""
    _do_table_count(reporter, schema, session, table)
    _do_table_size(reporter, schema, session, table)
    _do_indexes(reporter, schema, session, table)


def _do_indexes(
    reporter: Reporter,
    schema: str,
    session: scoped_session,
    table: str,
) -> None:
    for index_name, size_main, size_fsm, number_of_scans, tuples_read, tuples_fetched in session.execute(
        sqlalchemy.text(
            """
    SELECT
         foo.indexname,
         pg_relation_size(concat(quote_ident(foo.schemaname), '.', quote_ident(foo.indexrelname)), 'main'),
         pg_relation_size(concat(quote_ident(foo.schemaname), '.', quote_ident(foo.indexrelname)), 'fsm'),
         foo.idx_scan AS number_of_scans,
         foo.idx_tup_read AS tuples_read,
         foo.idx_tup_fetch AS tuples_fetched
    FROM pg_tables t
    JOIN
         (
            SELECT psai.schemaname, c.relname AS ctablename, ipg.relname AS indexname, idx_scan, idx_tup_read,
                   idx_tup_fetch, indexrelname FROM pg_index x
                JOIN pg_class c ON c.oid = x.indrelid
                JOIN pg_class ipg ON ipg.oid = x.indexrelid
                JOIN pg_stat_all_indexes psai ON x.indexrelid = psai.indexrelid
         ) AS foo
         ON t.tablename = foo.ctablename AND t.schemaname=foo.schemaname
    WHERE t.schemaname=:schema AND t.tablename=:table
    """
        ),
        params={"schema": schema, "table": table},
    ):
        for fork, value in (("main", size_main), ("fsm", size_fsm)):
            reporter.do_report(
                [schema, table, index_name, fork],
                value,
                kind="table_index_size",
                kind_help="Size of the index",
                tags={"schema": schema, "table": table, "index": index_name, "fork": fork},
            )
        for action, value in (("scan", number_of_scans), ("read", tuples_read), ("fetch", tuples_fetched)):
            reporter.do_report(
                [schema, table, index_name, action],
                value,
                kind="table_index_usage",
                kind_help="Usage of the index",
                tags={"schema": schema, "table": table, "index": index_name, "action": action},
            )


def _do_table_size(
    reporter: Reporter,
    schema: str,
    session: scoped_session,
    table: str,
) -> None:
    result = session.execute(
        sqlalchemy.text(
            """
    SELECT pg_table_size(c.oid) AS total_bytes
    FROM pg_class c
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE relkind = 'r' AND nspname=:schema AND relname=:table
    """
        ),
        params={"schema": schema, "table": table},
    ).fetchone()
    assert result is not None
    size: int
    (size,) = result
    reporter.do_report(
        [schema, table],
        size,
        kind="table_size",
        kind_help="Size of the table",
        tags={"schema": schema, "table": table},
    )


def _do_table_count(
    reporter: Reporter,
    schema: str,
    session: scoped_session,
    table: str,
) -> None:
    # We request and estimation of the count as a real count is very slow on big tables
    # and seems to cause replicating lags. This estimate is updated on ANALYZE and VACUUM.
    result = session.execute(
        sqlalchemy.text(
            "SELECT reltuples FROM pg_class where "
            "oid=(quote_ident(:schema) || '.' || quote_ident(:table))::regclass;"
        ),
        params={"schema": schema, "table": table},
    ).fetchone()
    assert result is not None
    (count,) = result
    reporter.do_report(
        [schema, table],
        count,
        kind="table_count",
        kind_help="The number of row in the table",
        tags={"schema": schema, "table": table},
    )


def do_extra(session: scoped_session, sql: str, kind: str, gauge_help: str, reporter: Reporter) -> None:
    """Do an extra report."""

    for metric, count in session.execute(sqlalchemy.text(sql)):
        reporter.do_report(
            str(metric).split("."), count, kind=kind, kind_help=gauge_help, tags={"metric": metric}
        )


def _do_dtats_db(args: argparse.Namespace) -> None:
    reporter = Reporter(args)
    try:
        engine = sqlalchemy.create_engine(args.db)
        factory = sqlalchemy.orm.sessionmaker(bind=engine)
        register(factory)
        session = sqlalchemy.orm.scoped_session(factory)
    except Exception as e:
        reporter.error(["connection"], e)
        raise

    tables = session.execute(
        sqlalchemy.text(
            """
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_type='BASE TABLE' AND table_schema IN :schemas
    """
        ),
        params={"schemas": tuple(args.schema)},
    ).fetchall()
    for schema, table in tables:
        LOG.info("Process table %s.%s.", schema, table)
        try:
            do_table(session, schema, table, reporter)
        except Exception as e:  # pylint: disable=broad-except
            LOG.exception("Process table %s.%s error.", schema, table)
            reporter.error([schema, table], e)

    if args.extra:
        for pos, extra in enumerate(args.extra):
            LOG.info("Process extra %s.", extra)
            try:
                do_extra(session, extra, "extra", "Extra metric", reporter)
            except Exception as e:  # pylint: disable=broad-except
                LOG.exception("Process extra %s error.", extra)
                reporter.error(["extra", str(pos + 1)], e)
    if args.extra_gauge:
        for pos, extra in enumerate(args.extra_gauge):
            sql, gauge, gauge_help = extra
            LOG.info("Process extra %s.", extra)
            try:
                do_extra(session, sql, gauge, gauge_help, reporter)
            except Exception as e:  # pylint: disable=broad-except
                LOG.exception("Process extra %s error.", extra)
                reporter.error(["extra", str(len(args.extra) + pos + 1)], e)

    reporter.commit()
    transaction.abort()
    reporter.report_error()


def main() -> None:
    """Run the command."""
    success = False
    args = _parse_args()
    c2cwsgiutils.setup_process.init(args.config_uri)
    for _ in range(int(os.environ.get("C2CWSGIUTILS_STATS_DB_TRYNUMBER", 10))):
        try:
            _do_dtats_db(args)
            success = True
            break
        except:  # pylint: disable=bare-except
            LOG.exception("Exception during run")
        time.sleep(float(os.environ.get("C2CWSGIUTILS_STATS_DB_SLEEP", 1)))

    if not success:
        LOG.error("Not in success, exiting")
        sys.exit(1)


if __name__ == "__main__":
    main()
