#!/usr/bin/env python3
import c2cwsgiutils.setup_process  # noqa  # pylint: disable=unused-import
from c2cwsgiutils import stats

import datetime
from dateutil import parser as dp
import logging
import os
import requests
from typing import Optional


def _ensure_slash(txt: Optional[str]) -> Optional[str]:
    if txt is None:
        return None
    if txt.endswith('/'):
        return txt
    return txt + '/'


LOG = logging.getLogger("check_elasticsearch")
ES_URL = _ensure_slash(os.environ.get('ES_URL'))
ES_INDEXES = os.environ.get('ES_INDEXES')
ES_AUTH = os.environ.get('ES_AUTH')
ES_FILTERS = os.environ.get('ES_FILTERS', '')

SEARCH_HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json"
}
if ES_AUTH is not None:
    SEARCH_HEADERS['Authorization'] = ES_AUTH
SEARCH_URL = f"{ES_URL}{ES_INDEXES}/_search"


def _max_timestamp() -> datetime.datetime:
    query = {
        'aggs': {
            "max_timestamp": {
                "max": {
                    "field": "@timestamp"
                }
            }
        }
    }
    if ES_FILTERS != "":
        query['query'] = {
            'bool': {
                'must': []
            }
        }
        for filter_ in ES_FILTERS.split(","):
            name, value = filter_.split("=")
            query['query']['bool']['must'].append({
                'term': {name: value}
            })
    r = requests.post(SEARCH_URL, json=query, headers=SEARCH_HEADERS)
    r.raise_for_status()
    json = r.json()
    return dp.parse(json['aggregations']['max_timestamp']['value_as_string'])


def main() -> None:
    with stats.outcome_timer_context(['get_max_timestamp']):
        max_ts = _max_timestamp()
    now = datetime.datetime.now(max_ts.tzinfo)
    age = round((now - max_ts).total_seconds())
    LOG.info("Last log age: %ss", age)
    stats.set_gauge(['max_age'], age)


main()
