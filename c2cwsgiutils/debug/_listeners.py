import gc
import sys
import threading
import time
import traceback
from typing import Any, Dict, List, Mapping, Optional, Tuple

from c2cwsgiutils import broadcast
from c2cwsgiutils.debug import get_size
import objgraph


def _dump_stacks_impl() -> Dict[str, Any]:
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    threads = {}
    for thread_id, stack in sys._current_frames().items():  # pylint: disable=W0212
        frames = []
        for filename, lineno, name, line in traceback.extract_stack(stack):
            cur = {
                'file': filename,
                'line': lineno,
                'function': name
            }
            if line:
                cur['code'] = line.strip()
            frames.append(cur)
        threads["%s(%d)" % (id2name.get(thread_id, ""), thread_id)] = frames
    return {
        'threads': threads
    }


def _dump_memory_impl(limit: int, analyze_type: Optional[str]) -> Mapping[str, Any]:
    nb_collected = [gc.collect(generation) for generation in range(3)]
    result = {
        'nb_collected': nb_collected,
        'most_common_types': objgraph.most_common_types(limit=limit, shortnames=False),
        'leaking_objects': objgraph.most_common_types(limit=limit, shortnames=False,
                                                      objects=objgraph.get_leaking_objects())
    }

    if analyze_type:
        # timeout after one minute, must be set to a bit less that the timeout of the broadcast in _views.py
        timeout = time.monotonic() + 60

        mod_counts: Dict[str, int] = {}
        biggest_objects: List[Tuple[int, Any]] = []
        result[analyze_type] = {}
        for obj in objgraph.by_type(analyze_type):
            if analyze_type == 'builtins.function':
                short = obj.__module__.split('.')[0] if obj.__module__ is not None else ""
                mod_counts[short] = mod_counts.get(short, 0) + 1
            else:
                size = get_size(obj)
                if len(biggest_objects) < limit or size > biggest_objects[0][0]:
                    biggest_objects.append((size, obj))
                    biggest_objects.sort(key=lambda x: x[0])
                    if len(biggest_objects) > limit:
                        biggest_objects = biggest_objects[-limit:]
            if time.monotonic() > timeout:
                result[analyze_type]['timeout'] = True
                break
        if analyze_type == 'builtins.function':
            result[analyze_type]['modules'] = [dict(module=i[0], nb_func=i[1])
                                               for i in sorted(mod_counts.items(),
                                                               key=lambda x: -x[1])[:limit]]
        elif analyze_type == 'linecache':
            import linecache
            cache = linecache.cache  # type: ignore
            result[analyze_type]['biggest_objects'] = sorted([dict(filename=k, size=get_size(v))
                                                              for k, v in cache.items()],
                                                             key=lambda i: -i['size'])
        else:
            biggest_objects.reverse()
            result[analyze_type]['biggest_objects'] = [dict(size=i[0], repr=repr(i[1]))
                                                       for i in biggest_objects]
    return result


def init() -> None:
    broadcast.subscribe('c2c_dump_memory', _dump_memory_impl)
    broadcast.subscribe('c2c_dump_stacks', _dump_stacks_impl)
