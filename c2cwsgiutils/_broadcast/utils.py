import os
import socket


def add_host_info(response):
    if isinstance(response, dict):
        response.update({
            'hostname': socket.gethostname(),
            'pid': os.getpid()
        })
    return response
