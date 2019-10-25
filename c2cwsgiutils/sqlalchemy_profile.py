"""
Reporter for sqlalchemy-easy-profile
"""

import logging
from typing import Dict, List

from easy_profile.profiler import DebugQuery
from easy_profile.reporters import Reporter

LOG = logging.getLogger(__name__)


class C2cReporter(Reporter):  # type: ignore
    def report(self, path: str, stats: Dict[str, List[DebugQuery]]) -> None:
        LOG.info('\n---\n'.join(['Query takes {}ms, for:\n{},\nwith:\n{}.'.format(
            query.duration * 1000, query.statement, query.parameters
        ) for query in stats['call_stack']]))
