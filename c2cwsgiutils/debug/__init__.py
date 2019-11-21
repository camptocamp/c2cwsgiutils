from collections import defaultdict
import gc
import logging
import re
import sys
from types import FunctionType, ModuleType
from typing import Any, Dict, List, Optional, Set

from c2cwsgiutils import _utils, auth
import pyramid.config

LOG = logging.getLogger(__name__)

CONFIG_KEY = 'c2c.debug_view_enabled'
ENV_KEY = 'C2C_DEBUG_VIEW_ENABLED'

# 7ff7d33bd000-7ff7d33be000 r--p 00000000 00:65 49                         /usr/lib/toto.so
SMAPS_LOCATION_RE = re.compile(r'^[0-9a-f]+-[0-9a-f]+ +.... +[0-9a-f]+ +[^ ]+ +\d+ +(.*)$')

# Size:                  4 kB
SMAPS_ENTRY_RE = re.compile(r'^([\w]+): +(\d+) kB$')


def init(config: pyramid.config.Configurator) -> None:
    if auth.is_enabled(config, ENV_KEY, CONFIG_KEY):
        from . import _views
        init_daemon(config)
        _views.init(config)


def init_daemon(config: Optional[pyramid.config.Configurator] = None) -> None:
    """
    Initialize the debug broadcast listeners. Used mostly for headless processes that depend on a master
    providing a normal REST API and broadcasting those requests.
    """
    if _utils.env_or_config(config, ENV_KEY, CONFIG_KEY, type_=_utils.config_bool):
        from . import _listeners
        _listeners.init()


BLACKLIST = type, ModuleType, FunctionType


def get_size(obj: Any) -> int:
    """sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        return 0
    seen_ids: Set[int] = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = gc.get_referents(*need_referents)
    return size


def dump_memory_maps(pid: str = 'self') -> List[Dict[str, Any]]:
    with open("/proc/{}/smaps".format(pid)) as input_:
        cur_dict: Dict[str, int] = defaultdict(int)
        sizes: Dict[str, Any] = {}
        for line in input_:
            line = line.rstrip("\n")
            matcher = SMAPS_LOCATION_RE.match(line)
            if matcher:
                cur_dict = sizes.setdefault(matcher.group(1), defaultdict(int))
            else:
                matcher = SMAPS_ENTRY_RE.match(line)
                if matcher:
                    name = matcher.group(1)
                    if name in ('Size', 'Rss', 'Pss'):
                        cur_dict[name.lower() + '_kb'] += int(matcher.group(2))
                elif not line.startswith("VmFlags:"):
                    LOG.warning("Don't know how to parse /proc/self/smaps line: %s", line)
        return [
            {'name': name, **value}
            for name, value in sizes.items()
            if value.get('pss_kb', 0) > 0
        ]
