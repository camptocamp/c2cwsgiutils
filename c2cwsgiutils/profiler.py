import contextlib
import cProfile
import pstats
import sys
from typing import Any


class Profile(contextlib.ContextDecorator):
    """Used to profile a function with a decorator or with a with statement."""

    def __init__(self, path: str, print_number: int = 0) -> None:
        self.path = path
        self.print_number = print_number
        self.pr = cProfile.Profile()

    def __enter__(self) -> None:
        self.pr.enable()

    def __exit__(self, *exc: Any) -> None:
        del exc

        self.pr.disable()
        self.pr.dump_stats(self.path)

        if self.print_number > 0:
            ps = pstats.Stats(self.pr, stream=sys.stdout).sort_stats(pstats.SortKey.CUMULATIVE)
            ps.print_stats(self.print_number)
