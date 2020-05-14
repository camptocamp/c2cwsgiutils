import os
import socket
from typing import Any


def add_host_info(response: Any) -> Any:
    if isinstance(response, dict):
        response.update({"hostname": socket.gethostname(), "pid": os.getpid()})
    return response
