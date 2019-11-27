import re
import logging
from typing import Any


class ContainsExpression(logging.Filter):
    """
    Returns True if the regex is matched in the log message
    """
    def __init__(self, regex: str) -> None:
        self.regex = re.compile(regex)

    def filter(self, record: Any) -> bool:
        return bool(self.regex.search(record.msg))


class DoesNotContainExpression(logging.Filter):
    """
    Returns True if the regex is NOT matched in the log message
    """
    def __init__(self, regex: str) -> None:
        self.regex = re.compile(regex)

    def filter(self, record: Any) -> bool:
        return not bool(self.regex.search(record.msg))
