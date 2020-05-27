from typing import Any

import sqlalchemy.event
from pyramid.threadlocal import get_current_request
from sqlalchemy.orm import Session


def _add_session_id(session: Session, _transaction: Any, _connection: Any) -> None:
    request = get_current_request()
    if request is not None:
        session.execute("set application_name=:session_id", params={"session_id": request.c2c_request_id})


def init() -> None:
    sqlalchemy.event.listen(Session, "after_begin", _add_session_id)
