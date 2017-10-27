import logging
import objgraph
import threading
import time
import traceback
import sys

from c2cwsgiutils import _utils, _auth

CONFIG_KEY = 'c2c.debug_view_secret'
ENV_KEY = 'DEBUG_VIEW_SECRET'

LOG = logging.getLogger(__name__)


def _dump_stacks(request):
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():  # pylint: disable=W0212
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId, ""), threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    return "\n".join(code)


def _dump_memory(request):
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    limit = int(request.params.get('limit', '30'))
    nb_collected = objgraph.gc.collect()
    return {
        'nb_collected': nb_collected,
        'most_common_types': objgraph.most_common_types(limit=limit, shortnames=False),
        'leaking_objects': objgraph.most_common_types(limit=limit, shortnames=False,
                                                      objects=objgraph.get_leaking_objects())
    }


def _sleep(request):
    _auth.auth_view(request, ENV_KEY, CONFIG_KEY)
    timeout = float(request.params['time'])
    time.sleep(timeout)
    request.response.status_code = 204
    return request.response


def init(config):
    if _utils.env_or_config(config, ENV_KEY, CONFIG_KEY, False):
        config.add_route("c2c_debug_stacks", _utils.get_base_path(config) + r"/debug/stacks",
                         request_method="GET")
        config.add_view(_dump_stacks, route_name="c2c_debug_stacks", renderer="string", http_cache=0)

        config.add_route("c2c_debug_memory", _utils.get_base_path(config) + r"/debug/memory",
                         request_method="GET")
        config.add_view(_dump_memory, route_name="c2c_debug_memory", renderer="json", http_cache=0)

        config.add_route("c2c_debug_sleep", _utils.get_base_path(config) + r"/debug/sleep",
                         request_method="GET")
        config.add_view(_sleep, route_name="c2c_debug_sleep", renderer="json", http_cache=0)

        LOG.info("Enabled the /debug/stacks API")
