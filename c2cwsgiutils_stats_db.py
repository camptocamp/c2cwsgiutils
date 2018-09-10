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
            self.statsd = stats.StatsDBackend(args.statsd_address, args.statsd_prefix)
        else:
            self.statsd = None

        if args.prometheus_url:
            self.prometheus = PushgatewayGroupPublisher(args.prometheus_url, 'db_counts',
                                                        instance=args.prometheus_instance)
        else:
            self.prometheus = None

    def do_report(self, metric, value, kind='count'):
        LOG.info("%s.%s -> %d", kind, ".".join(metric), value)
        if self.statsd is not None:
            self.statsd.gauge([kind] + metric, value)
        if self.prometheus is not None:

            self.prometheus.add('database_table_' + kind, value, metric_labels={
                'metric': ".".join(v.replace('.', '_') for v in metric)
            })

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
    count, = session.execute("""
    SELECT count(*) FROM {schema}.{table}
    """.format(schema=schema, table=table)).fetchone()
    reporter.do_report([schema, table], count, kind='count')

    size, = session.execute("""
    SELECT pg_total_relation_size(c.oid) AS total_bytes
    FROM pg_class c
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE relkind = 'r' AND nspname=:schema AND relname=:table
    """, params={'schema': schema, 'table': table}).fetchone()
    reporter.do_report([schema, table], size, kind='size')


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
