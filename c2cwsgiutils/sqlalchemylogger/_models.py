from typing import Any, Union

from sqlalchemy import Column
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime, Integer, String

Base = declarative_base()


def create_log_class(tablename: str = "logs", tableargs: Union[str, dict[str, str]] = "") -> Any:
    """Get the sqlalchemy lgo class."""

    class Log(Base):  # type: ignore
        """The SQLAlchemy class that represent the log table."""

        __table_args__ = tableargs
        __tablename__ = tablename
        id = Column(Integer, primary_key=True)  # auto incrementing
        logger = Column(String)  # the name of the logger. (e.g. myapp.views)
        level = Column(String)  # info, debug, or error?
        trace = Column(String)  # the full traceback printout
        msg = Column(String)  # any custom log you may have included
        created_at = Column(  # the current timestamp
            DateTime,
            default=func.now(),  # pylint: disable=not-callable
        )

        def __init__(self, logger: Any = None, level: Any = None, trace: Any = None, msg: Any = None) -> None:
            self.logger = logger
            self.level = level
            self.trace = trace
            self.msg = msg

        def __unicode__(self) -> str:
            return self.__repr__()

        def __repr__(self) -> str:
            return f"<Log: {self.created_at.strftime('%m/%d/%Y-%H:%M:%S')} - {self.msg[:50]}>"

    return Log
