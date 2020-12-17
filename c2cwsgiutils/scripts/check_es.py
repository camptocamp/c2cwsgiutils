#!/usr/bin/env python3
import datetime
import logging
import os
import time
import uuid
from typing import Any, List, Optional

import requests
from dateutil import parser as dp

import c2cwsgiutils.setup_process
from c2cwsgiutils import stats


def _ensure_slash(txt: Optional[str]) -> Optional[str]:
    if txt is None:
        return None
    if txt.endswith("/"):
        return txt
    return txt + "/"


LOGGER_NAME = "check_elasticsearch"
LOG_TIMEOUT = int(os.environ["LOG_TIMEOUT"])
LOG = logging.getLogger(LOGGER_NAME)
ES_URL = _ensure_slash(os.environ.get("ES_URL"))
ES_INDEXES = os.environ.get("ES_INDEXES")
ES_AUTH = os.environ.get("ES_AUTH")
ES_FILTERS = os.environ.get("ES_FILTERS", "")

SEARCH_HEADERS = {"Content-Type": "application/json;charset=UTF-8", "Accept": "application/json"}
if ES_AUTH is not None:
    SEARCH_HEADERS["Authorization"] = ES_AUTH
SEARCH_URL = f"{ES_URL}{ES_INDEXES}/_search"


def _max_timestamp() -> datetime.datetime:
    must: List[Any] = []
    query = {
        "aggs": {"max_timestamp": {"max": {"field": "@timestamp"}}},
        "query": {"bool": {"must": must}},
    }
    if ES_FILTERS != "":
        for filter_ in ES_FILTERS.split(","):
            name, value = filter_.split("=")
            must.append({"term": {name: value}})
    else:
        del query["query"]

    r = requests.post(SEARCH_URL, json=query, headers=SEARCH_HEADERS)
    r.raise_for_status()
    json = r.json()
    return dp.parse(json["aggregations"]["max_timestamp"]["value_as_string"])


def _check_roundtrip() -> None:
    check_uuid = str(uuid.uuid4())

    # emit the log we are going to look for
    logger_name = LOGGER_NAME + "." + check_uuid
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.info("Test roundtrip")

    query = {"query": {"match_phrase": {"log.logger": logger_name}}}
    start = time.monotonic()
    while time.monotonic() < start + LOG_TIMEOUT:
        r = requests.post(SEARCH_URL, json=query, headers=SEARCH_HEADERS)
        r.raise_for_status()
        json = r.json()
        found = json["hits"]["total"]
        if found > 0:
            LOG.info("Found the test log line.")
            stats.set_gauge(["roundtrip"], time.monotonic() - start)
            return
        else:
            LOG.info("Didn't find the test log line. Wait 1s...")
            time.sleep(1)
    LOG.warning("Timeout waiting for the test log line")
    stats.set_gauge(["roundtrip"], LOG_TIMEOUT * 2)


def deprecated() -> None:
    LOG.warning("c2cwsgiutils_check_es.py is deprecated; use c2cwsgiutils-check-es instead")
    return main()


def main() -> None:
    c2cwsgiutils.setup_process.init()

    with stats.outcome_timer_context(["get_max_timestamp"]):
        max_ts = _max_timestamp()
    now = datetime.datetime.now(max_ts.tzinfo)
    age = round((now - max_ts).total_seconds())
    LOG.info("Last log age: %ss", age)
    stats.set_gauge(["max_age"], age)

    if "LOG_TIMEOUT" in os.environ:
        _check_roundtrip()


if __name__ == "__main__":
    main()
