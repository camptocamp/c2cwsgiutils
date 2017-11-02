"""
Monkey patch standard functions to improve their behavior
"""

import ipaddress
import random
import socket
from typing import Tuple, List, Any, Callable

_orig_socket_getaddrinfo = socket.getaddrinfo
_orig_socket_gethostbyname_ex = socket.gethostbyname_ex


def randomized_socket_getaddrinfo(
        *args: Any, **kwargs: Any) -> List[Tuple[int, int, int, str, Tuple[Any, ...]]]:
    """
    socket.getaddrinfo is not DNS roundrobin friendly. This randomizes it.
    """
    result = _orig_socket_getaddrinfo(*args, **kwargs)
    return _shuffle_addresses(result, lambda entry: entry[4][0])


def randomized_socket_gethostbyname_ex(hostname: str) -> Tuple[str, List[str], List[str]]:  # pragma: no cover
    """
    socket.gethostbyname_ex is not DNS roundrobin friendly. This randomizes it.
    """
    hostname, aliaslist, ipaddrlist = _orig_socket_gethostbyname_ex(hostname)
    ipaddrlist = _shuffle_addresses(ipaddrlist, lambda entry: entry)
    return hostname, aliaslist, ipaddrlist


def randomized_socket_gethostbyname(hostname: str) -> str:  # pragma: no cover
    """
    socket.gethostbyname is not DNS roundrobin friendly. This randomizes it.
    """
    result = _orig_socket_gethostbyname_ex(hostname)
    return random.choice(result[2])


def init() -> None:
    socket.getaddrinfo = randomized_socket_getaddrinfo
    socket.gethostbyname_ex = randomized_socket_gethostbyname_ex
    socket.gethostbyname = randomized_socket_gethostbyname


def _shuffle_addresses(entries: list, get_address: Callable[[Any], str]) -> list:
    """
    Randomizes the given addresses, but keep the order between address types. For example, if the IPv4
    addresses were first, they will stay first
    """
    if len(entries) <= 1:
        return entries
    v4 = []
    v6 = []
    what_first = None
    for entry in entries:
        addr = get_address(entry)
        version = ipaddress.ip_address(addr).version
        if version == 4:
            v4.append(entry)
        else:
            v6.append(entry)
        if what_first is None:
            what_first = version

    if len(v4) > 1:
        random.shuffle(v4)
    if len(v6) > 1:
        random.shuffle(v6)

    return v4 + v6 if what_first == 4 else v6 + v4
