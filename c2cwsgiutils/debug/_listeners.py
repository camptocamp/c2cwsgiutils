import gc
import sys
import threading
import time
import traceback
from collections.abc import Mapping
from typing import Any, Optional, cast

import objgraph

from c2cwsgiutils import broadcast
from c2cwsgiutils.debug.utils import get_size

FILES_FIELDS = {"__name__", "__doc__", "__package__", "__loader__", "__spec__", "__file__"}


def _dump_stacks_impl() -> dict[str, Any]:
    id2name = {th.ident: th.name for th in threading.enumerate()}
    threads = {}
    for thread_id, stack in sys._current_frames().items():  # pylint: disable=W0212
        frames = []
        for filename, lineno, name, line in traceback.extract_stack(stack):
            cur = {"file": filename, "line": lineno, "function": name}
            if line:
                cur["code"] = line.strip()
            frames.append(cur)
        threads[f"{id2name.get(thread_id, '')}({thread_id:d})"] = frames
    return {"threads": threads}


# pylint: disable=too-many-branches
def _dump_memory_impl(
    limit: int,
    analyze_type: Optional[str],
    python_internals_map: bool = False,
) -> Mapping[str, Any]:
    nb_collected = [gc.collect(generation) for generation in range(3)]
    result = {
        "nb_collected": nb_collected,
        "most_common_types": objgraph.most_common_types(limit=limit, shortnames=False),
        "leaking_objects": objgraph.most_common_types(
            limit=limit, shortnames=False, objects=objgraph.get_leaking_objects()
        ),
    }

    if python_internals_map and not analyze_type:
        analyze_type = "builtins.dict"

    if analyze_type:
        # timeout after one minute, must be set to a bit less that the timeout of the broadcast in _views.py
        timeout = time.perf_counter() + 60

        mod_counts: dict[str, int] = {}
        biggest_objects: list[tuple[float, Any]] = []
        result[analyze_type] = {}
        for obj in objgraph.by_type(analyze_type):
            if analyze_type == "builtins.function":
                short = obj.__module__.split(".")[0] if obj.__module__ is not None else ""
                mod_counts[short] = mod_counts.get(short, 0) + 1
            else:
                if analyze_type == "builtins.dict":
                    python_internal = False
                    if not (FILES_FIELDS - set(obj.keys())):
                        python_internal = True
                    if (
                        not ({"scope", "module", "locals", "globals"} - set(obj.keys()))
                        and isinstance(obj["globals"], dict)
                        and not (FILES_FIELDS - set(obj["globals"].keys()))
                    ):
                        python_internal = True
                    if (
                        python_internal
                        and not python_internals_map
                        or not python_internal
                        and python_internals_map
                    ):
                        continue
                size = get_size(obj) / 1024
                if len(biggest_objects) < limit or size > biggest_objects[0][0]:
                    biggest_objects.append((size, obj))
                    biggest_objects.sort(key=lambda x: x[0])
                    if len(biggest_objects) > limit:
                        biggest_objects = biggest_objects[-limit:]
            if time.perf_counter() > timeout:
                result[analyze_type]["timeout"] = True
                break
        if analyze_type == "builtins.function":
            result[analyze_type]["modules"] = [
                {"module": i[0], "nb_func": i[1]}
                for i in sorted(mod_counts.items(), key=lambda x: -x[1])[:limit]
            ]
        elif analyze_type == "linecache":
            import linecache

            cache = linecache.cache
            result[analyze_type]["biggest_objects"] = sorted(
                ({"filename": k, "size_kb": get_size(v)} for k, v in cache.items()),
                key=lambda i: -(cast(int, i["size_kb"])),
            )
        else:
            biggest_objects.reverse()
            result[analyze_type]["biggest_objects"] = [
                {"size_kb": i[0], "repr": repr(i[1])} for i in biggest_objects
            ]
    return result


def init() -> None:
    """Initialize the debug listeners."""
    broadcast.subscribe("c2c_dump_memory", _dump_memory_impl)
    broadcast.subscribe("c2c_dump_stacks", _dump_stacks_impl)
