import re
import logging


class ContainsExpression(logging.Filter):
    """
    Returns True if the regex is matched in the log message
    """
    def __init__(self, regex):
        self.regex = re.compile(regex)

    def filter(self, record):
        return bool(self.regex.search(record.msg))


class DoesNotContainExpression(logging.Filter):
    """
    Returns True if the regex is NOT matched in the log message
    """
    def __init__(self, regex):
        self.regex = re.compile(regex)

    def filter(self, record):
        return not bool(self.regex.search(record.msg))

