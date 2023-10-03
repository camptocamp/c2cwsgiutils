from typing import Any

import sqlalchemy.event
from pyramid.threadlocal import get_current_request
from sqlalchemy.orm import Session


def _add_session_id(session: Session, _transaction: Any) -> None:
    request = get_current_request()
    if request is not None:
        session.execute(
            sqlalchemy.text("set application_name=:session_id"), params={"session_id": request.c2c_request_id}
        )


def init() -> None:
    """Initialize the SQL alchemy session selector."""

    sqlalchemy.event.listen(Session, "after_transaction_create", _add_session_id)
