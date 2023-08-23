from collections import defaultdict
import gc
import logging
import os
import re
import sys
from types import FunctionType, ModuleType
from typing import Any

# 7ff7d33bd000-7ff7d33be000 r--p 00000000 00:65 49                         /usr/lib/toto.so
SMAPS_LOCATION_RE = re.compile(r"^[0-9a-f]+-[0-9a-f]+ +.... +[0-9a-f]+ +[^ ]+ +\d+ +(.*)$")

# Size:                  4 kB
SMAPS_ENTRY_RE = re.compile(r"^([\w]+): +(\d+) kB$")

BLACKLIST = type, ModuleType, FunctionType
LOG = logging.getLogger(__name__)


def get_size(obj: Any) -> int:
    """Get the sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        return 0
    seen_ids: set[int] = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj_ in objects:
            if not isinstance(obj_, BLACKLIST) and id(obj_) not in seen_ids:
                seen_ids.add(id(obj_))
                size += sys.getsizeof(obj_)
                need_referents.append(obj_)
        objects = gc.get_referents(*need_referents)
    return size


def dump_memory_maps(pid: str = "self") -> list[dict[str, Any]]:
    """Get the Linux memory maps."""
    filename = os.path.join("/proc", pid, "smaps")
    if not os.path.exists(filename):
        return []
    with open(filename, encoding="utf-8") as input_:
        cur_dict: dict[str, int] = defaultdict(int)
        sizes: dict[str, Any] = {}
        for line in input_:
            line = line.rstrip("\n")
            matcher = SMAPS_LOCATION_RE.match(line)
            if matcher:
                cur_dict = sizes.setdefault(matcher.group(1), defaultdict(int))
            else:
                matcher = SMAPS_ENTRY_RE.match(line)
                if matcher:
                    name = matcher.group(1)
                    if name in ("Size", "Rss", "Pss"):
                        cur_dict[name.lower() + "_kb"] += int(matcher.group(2))
                elif (
                    not line.startswith("VmFlags:")
                    and not line.startswith("ProtectionKey:")
                    and not line.startswith("THPeligible:")
                ):
                    LOG.debug("Don't know how to parse /proc/%s/smaps line: %s", pid, line)
        return [{"name": name, **value} for name, value in sizes.items() if value.get("pss_kb", 0) > 0]
