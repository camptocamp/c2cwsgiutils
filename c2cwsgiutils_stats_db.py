#!/usr/bin/env python3
"""
Emits statsd gauges for every tables of a database.
"""
import argparse
import logging
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.exc
import sys
import transaction
from zope.sqlalchemy import ZopeTransactionExtension

from c2cwsgiutils import stats
from c2cwsgiutils.prometheus import PushgatewayGroupPublisher

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)-15s %(levelname)5s %(name)s %(message)s",
                    stream=sys.stdout)
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
        if args.statsd_address:
            self.statsd = stats._StatsDBackend(args.statsd_address, args.statsd_prefix)
        else:
            self.statsd = None

        if args.prometheus_url:
            self.prometheus = PushgatewayGroupPublisher(args.prometheus_url, 'db_counts',
                                                        instance=args.prometheus_instance)
        else:
            self.prometheus = None

    def do_report(self, metric, count):
        LOG.info("%s -> %d", ".".join(metric), count)
        if self.statsd is not None:
            self.statsd.gauge(metric, count)
        if self.prometheus is not None:

            self.prometheus.add('database_table_count', count, metric_labels={
                'metric': ".".join(v.replace('.', '_') for v in metric)
            })

    def commit(self):
        if self.prometheus is not None:
            self.prometheus.commit()


def error(self, metric):
        if self.statsd is not None:
            self.statsd.counter(['error'] + metric, 1)


def do_table(session, schema, table, reporter):
    count, = session.execute("""
    SELECT count(*) FROM {schema}.{table}
    """.format(schema=schema, table=table)).fetchone()
    reporter.do_report([schema, table], count)


def do_extra(session, extra, reporter):
    for metric, count in session.execute(extra):
        reporter.do_report(str(metric).split("."), count)


def main():
    args = _parse_args()
    reporter = Reporter(args)
    try:
        engine = sqlalchemy.create_engine(args.db)
        session = sqlalchemy.orm.scoped_session(
            sqlalchemy.orm.sessionmaker(extension=ZopeTransactionExtension(), bind=engine))()
    except Exception:
        reporter.error(['connection'])
        raise

    tables = session.execute("""
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_type='BASE TABLE' AND table_schema IN :schemas
    """, params={'schemas': tuple(args.schema)})
    for schema, table in tables:
        try:
            do_table(session, schema, table, reporter)
        except Exception:
            reporter.error([schema, table])

    if args.extra:
        for pos, extra in enumerate(args.extra):
            try:
                do_extra(session, extra, reporter)
            except Exception:
                reporter.error(['extra', str(pos + 1)])

    reporter.commit()
    transaction.abort()


if __name__ == '__main__':
    main()
