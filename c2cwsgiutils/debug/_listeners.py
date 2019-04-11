import gc
import objgraph
import sys
import threading
import traceback
from typing import Dict, Any, Mapping

from c2cwsgiutils import broadcast


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


def _dump_memory_impl(limit: int) -> Mapping[str, Any]:
    nb_collected = [gc.collect(generation) for generation in range(3)]
    return {
        'nb_collected': nb_collected,
        'most_common_types': objgraph.most_common_types(limit=limit, shortnames=False),
        'leaking_objects': objgraph.most_common_types(limit=limit, shortnames=False,
                                                      objects=objgraph.get_leaking_objects())
    }


def init() -> None:
    broadcast.subscribe('c2c_dump_memory', _dump_memory_impl)
    broadcast.subscribe('c2c_dump_stacks', _dump_stacks_impl)
