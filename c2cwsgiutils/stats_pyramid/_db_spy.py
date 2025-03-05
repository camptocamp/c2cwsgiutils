import logging
import re
import time
from collections.abc import Callable
from typing import Any

import prometheus_client
import sqlalchemy.event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from c2cwsgiutils import prometheus

_LOG = logging.getLogger(__name__)

_PROMETHEUS_DB_SUMMARY = prometheus_client.Summary(
    prometheus.build_metric_name("database"),
    "Database requests",
    ["what"],
    unit="seconds",
)


def _jump_string(content: str, pos: int) -> int:
    quote_char = content[pos]
    pos += 1
    while pos < len(content):
        cur = content[pos]
        if cur == quote_char:
            if pos + 1 < len(content) and content[pos + 1] == quote_char:
                pos += 1
            else:
                return pos
        pos += 1
    return pos


def _eat_parenthesis(content: str) -> str:
    depth = 0
    pos = 0
    while pos < len(content):
        cur = content[pos]
        if cur == "(":
            depth += 1
        elif cur == ")":
            depth -= 1
            if depth == 0:
                pos += 1
                break
        elif cur in ('"', "'"):
            pos = _jump_string(content, pos)
        pos += 1
    return content[pos:]


def _simplify_sql(sql: str) -> str:
    """Simplify SQL statements to make them easier on the eye and shorter for the stats."""
    sql = " ".join(sql.split("\n"))
    sql = re.sub(r"  +", " ", sql)
    sql = re.sub(r"SELECT .*? FROM", "SELECT FROM", sql)
    sql = re.sub(r"INSERT INTO (.*?) \(.*", r"INSERT INTO \1", sql)
    sql = re.sub(r"SET .*? WHERE", "SET WHERE", sql)
    for in_ in reversed(list(re.compile(r" IN \(").finditer(sql))):
        before = sql[0 : in_.start()]
        after = _eat_parenthesis(sql[in_.end() - 1 :])
        sql = before + " IN (?)" + after
    return re.sub(r"%\(\w+\)\w", "?", sql)


def _create_sqlalchemy_timer_cb(what: str) -> Callable[..., Any]:
    start = time.perf_counter()

    def after(*_args: Any, **_kwargs: Any) -> None:
        _PROMETHEUS_DB_SUMMARY.labels({"query": what}).observe(time.perf_counter() - start)
        _LOG.debug("Execute statement '%s' in %d.", what, time.perf_counter() - start)

    return after


def _before_cursor_execute(
    conn: Connection,
    _cursor: Any,
    statement: str,
    _parameters: Any,
    _context: Any,
    _executemany: Any,
) -> None:
    sqlalchemy.event.listen(
        conn,
        "after_cursor_execute",
        _create_sqlalchemy_timer_cb(_simplify_sql(statement)),
        once=True,
    )


def _before_commit(session: Session) -> None:  # pragma: nocover
    sqlalchemy.event.listen(session, "after_commit", _create_sqlalchemy_timer_cb("commit"), once=True)


def init() -> None:  # pragma: nocover
    """Subscribe to SQLAlchemy events in order to get some stats on DB interactions."""
    sqlalchemy.event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
    sqlalchemy.event.listen(Session, "before_commit", _before_commit)
