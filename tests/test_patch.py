from c2cwsgiutils import _patches
import socket


def test_shuffle_addresses():
    shuffle = _patches._shuffle_addresses  # pylint: disable=W0212

    # check we keep v6/v4 ordering
    for _ in range(10):
        assert shuffle(['1.2.3.4', '1:2:3::4'], lambda x: x) == ['1.2.3.4', '1:2:3::4']
        assert shuffle(['1:2:3::4', '1.2.3.4'], lambda x: x) == ['1:2:3::4', '1.2.3.4']

    assert shuffle(['1.2.3.4'], lambda x: x) == ['1.2.3.4']
    assert shuffle(['1:2:3::4'], lambda x: x) == ['1:2:3::4']

    assert set(shuffle(['1.2.3.4', '1.2.3.5', '1.2.3.6'], lambda x: x)) == {'1.2.3.4', '1.2.3.5', '1.2.3.6'}

    not_shuffled = True
    orig = ['1.2.3.4', '1.2.3.5', '1.2.3.6']
    for _ in range(50):
        not_shuffled = not_shuffled and shuffle(orig, lambda x: x) == orig
    assert not not_shuffled


def test_randomized_socket_getaddrinfo():
    result = _patches.randomized_socket_getaddrinfo('www.thus.ch', 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    assert len(result) >= 1
    for _family, type_, proto, _canonname, sockaddr in result:
        assert type_ == socket.SOCK_STREAM
        assert proto == socket.SOL_TCP
        assert sockaddr[1] == 80


def test_randomized_socket_gethostbyname_ex():
    hostname, aliaslist, ipaddrlist = _patches.randomized_socket_gethostbyname_ex('www.thus.ch')
    assert isinstance(hostname, str)
    assert isinstance(aliaslist, list)
    assert isinstance(ipaddrlist, list)
    assert len(ipaddrlist) >= 1


def test_randomized_socket_gethostbyname():
    ipaddr = _patches.randomized_socket_gethostbyname('www.thus.ch')
    assert isinstance(ipaddr, str)
