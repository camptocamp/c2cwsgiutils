#!/usr/bin/env python3
"""
Emits statsd gauges for every tables of a database.
"""
import c2cwsgiutils.setup_process  # noqa  # pylint: disable=unused-import
import argparse
import logging
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.exc
import transaction
from zope.sqlalchemy import ZopeTransactionExtension

from c2cwsgiutils import stats, sentry
from c2cwsgiutils.prometheus import PushgatewayGroupPublisher

LOG = logging.getLogger("stats_db")


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=str, required=True, help='DB connection string')
    parser.add_argument('--schema', type=str, action='append', required=True, default=['public'],
                        help="schema to dump")
    parser.add_argument('--extra', type=str, action='append',
                        help='A SQL query that returns a metric name and a value')
    parser.add_argument('--statsd_address', type=str, help='address:port for the statsd daemon')
    parser.add_argument('--statsd_prefix', type=str, default='c2c', help='prefix for the statsd metrics')
    parser.add_argument('--prometheus_url', type=str, help='Base URL for the Prometheus Pushgateway')
    parser.add_argument('--prometheus_instance', type=str,
                        help='Instance name for the Prometheus Pushgateway')
    parser.add_argument('--verbosity', type=str, default='INFO')
    args = parser.parse_args()
    logging.root.setLevel(args.verbosity)
    return args


class Reporter(object):
    def __init__(self, args):
        self._error = None
        if args.statsd_address:
            self.statsd = stats.StatsDBackend(args.statsd_address, args.statsd_prefix,
                                              tags=stats.get_env_tags())
        else:
            self.statsd = None

        if args.prometheus_url:
            self.prometheus = PushgatewayGroupPublisher(args.prometheus_url, 'db_counts',
                                                        instance=args.prometheus_instance,
                                                        labels=stats.get_env_tags())
        else:
            self.prometheus = None

    def do_report(self, metric, value, kind, tags=None):
        LOG.info("%s.%s -> %d", kind, ".".join(metric), value)
        if self.statsd is not None:
            if stats.USE_TAGS and tags is not None:
                self.statsd.gauge([kind], value, tags=tags)
            else:
                self.statsd.gauge([kind] + metric, value)
        if self.prometheus is not None:

            self.prometheus.add('database_table_' + kind, value, metric_labels=tags)

    def commit(self):
        if self.prometheus is not None:
            self.prometheus.commit()

    def error(self, metric, e):
        if self.statsd is not None:
            self.statsd.counter(['error'] + metric, 1)
        if self._error is None:
            self._error = e

    def report_error(self):
        if self._error is not None:
            raise self._error


def do_table(session, schema, table, reporter):
    _do_table_count(reporter, schema, session, table)
    _do_table_size(reporter, schema, session, table)
    _do_indexes(reporter, schema, session, table)


def _do_indexes(reporter, schema, session, table):
    for index_name, size_main, size_fsm, size_vm, size_init, number_of_scans, tuples_read, tuples_fetched in \
            session.execute("""
    SELECT
         foo.indexname,
         pg_relation_size(concat(quote_ident(foo.schemaname), '.', quote_ident(foo.indexrelname)), 'main'),
         pg_relation_size(concat(quote_ident(foo.schemaname), '.', quote_ident(foo.indexrelname)), 'fsm'),
         pg_relation_size(concat(quote_ident(foo.schemaname), '.', quote_ident(foo.indexrelname)), 'vm'),
         pg_relation_size(concat(quote_ident(foo.schemaname), '.', quote_ident(foo.indexrelname)), 'init'),
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
    """, params={'schema': schema, 'table': table}):
        for fork, value in (('main', size_main), ('fsm', size_fsm), ('vm', size_vm), ('init', size_init)):
            reporter.do_report([schema, table, index_name, fork], value, kind='index_size',
                               tags=dict(schema=schema, table=table, index=index_name, fork=fork))
        for action, value in (('scan', number_of_scans), ('read', tuples_read), ('fetch', tuples_fetched)):
            reporter.do_report([schema, table, index_name, action], value, kind='index_usage',
                               tags=dict(schema=schema, table=table, index=index_name, action=action))


def _do_table_size(reporter, schema, session, table):
    size, = session.execute("""
    SELECT pg_table_size(c.oid) AS total_bytes
    FROM pg_class c
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE relkind = 'r' AND nspname=:schema AND relname=:table
    """, params={'schema': schema, 'table': table}).fetchone()
    reporter.do_report([schema, table], size, kind='size', tags=dict(schema=schema, table=table))


def _do_table_count(reporter, schema, session, table):
    quote = session.bind.dialect.identifier_preparer.quote
    count, = session.execute("""
    SELECT count(*) FROM {schema}.{table}
    """.format(schema=quote(schema), table=quote(table))).fetchone()  # nosec
    reporter.do_report([schema, table], count, kind='count', tags=dict(schema=schema, table=table))


def do_extra(session, extra, reporter):
    for metric, count in session.execute(extra):
        reporter.do_report(str(metric).split("."), count, kind='count')


def main():
    args = _parse_args()
    reporter = Reporter(args)
    try:
        engine = sqlalchemy.create_engine(args.db)
        session = sqlalchemy.orm.scoped_session(
            sqlalchemy.orm.sessionmaker(extension=ZopeTransactionExtension(), bind=engine))()
    except Exception as e:
        reporter.error(['connection'], e)
        raise

    tables = session.execute("""
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_type='BASE TABLE' AND table_schema IN :schemas
    """, params={'schemas': tuple(args.schema)})
    for schema, table in tables:
        try:
            do_table(session, schema, table, reporter)
        except Exception as e:
            reporter.error([schema, table], e)

    if args.extra:
        for pos, extra in enumerate(args.extra):
            try:
                do_extra(session, extra, reporter)
            except Exception as e:
                reporter.error(['extra', str(pos + 1)], e)

    reporter.commit()
    transaction.abort()
    reporter.report_error()


if __name__ == '__main__':
    sentry.init()
    main()
