import json
import logging
import select
import socket
import threading

from c2cwsgiutils.acceptance import retry

LOG = logging.getLogger(__name__)


def _query(app_connection, params, expected=None):
    all_params = {'secret': 'changeme'}
    all_params.update(params)
    response = app_connection.get_json('c2c/logging/level', params=all_params)

    all_expected = {'status': 200}
    if 'name' in all_params:
        all_expected['name'] = all_params['name']
    all_expected.update(expected)
    assert response == all_expected


def test_api(app_connection):
    _query(app_connection, {'name': 'sqlalchemy.engine'}, {'level': 'DEBUG', 'effective_level': 'DEBUG'})
    _query(app_connection, {'name': 'sqlalchemy.engine.sub'}, {'level': 'NOTSET', 'effective_level': 'DEBUG'})

    _query(app_connection, {'name': 'sqlalchemy.engine', 'level': 'INFO'},
           {'level': 'INFO', 'effective_level': 'INFO'})

    _query(app_connection, {'name': 'sqlalchemy.engine'}, {'level': 'INFO', 'effective_level': 'INFO'})
    _query(app_connection, {'name': 'sqlalchemy.engine.sub'}, {'level': 'NOTSET', 'effective_level': 'INFO'})

    _query(app_connection, {'name': 'sqlalchemy.engine', 'level': 'DEBUG'},
           {'level': 'DEBUG', 'effective_level': 'DEBUG'})

    _query(app_connection, {}, {'overrides': {'sqlalchemy.engine': 'DEBUG'}})


def test_api_bad_secret(app_connection):
    app_connection.get_json('c2c/logging/level', params={'secret': 'wrong', 'name': 'sqlalchemy.engine'},
                            expected_status=403)


def test_api_missing_secret(app_connection):
    app_connection.get_json('c2c/logging/level', params={'name': 'sqlalchemy.engine'}, expected_status=403)


class LogListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(('0.0.0.0', 514))  # nosec
        self._sock.setblocking(0)
        self._run = True
        self._condition = threading.Condition()
        self._messages = []

    def run(self):
        LOG.info("Starting to listen the logs")
        while self._run:
            ready = select.select([self._sock], [], [], 0.05)
            if ready[0]:
                data, _addr = self._sock.recvfrom(10240)
                data = data.decode('utf-8')
                pos_cee = data.find("@cee: ")
                if pos_cee >= 0:
                    pos_cee += 6
                    data = data[pos_cee:]
                    if data.endswith('\000'):
                        data = data[:-1]
                    parsed = json.loads(data)
                    with self._condition:
                        self._messages.append(parsed)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        LOG.info("Stopping the listener")
        self._run = False
        self.join()
        self._sock.close()
        LOG.info("Listener stopped")

    def get_messages(self, filter_fun=lambda message: True):
        with self._condition:
            if not self._messages:
                self._condition.wait(10)
            if len(self._messages) == 0:
                return []  # timeout
            result = self._messages
            self._messages = []
            return list(filter(filter_fun, result))


@retry(Exception)
def test_cee_logs(app_connection):
    with LogListener() as listener:
        app_connection.get_json("ping")
        messages = listener.get_messages(
            filter_fun=lambda message: message.get('facility') == 'c2cwsgiutils_app.services.ping')
        print("Got messages: " + repr(messages))
        assert len(messages) == 1
        message = messages[0]
        assert message['short_message'] == 'Ping!'
        assert message['level'] == 6
        assert message['level_name'] == 'INFO'
        assert 'request_id' in message


@retry(Exception)
def test_cee_logs_request_id(app_connection):
    with LogListener() as listener:
        app_connection.get_json("ping", headers={'X-Request-ID': '42 is the answer'})
        messages = listener.get_messages(
            filter_fun=lambda message: message.get('facility') == 'c2cwsgiutils_app.services.ping')
        print("Got messages: " + repr(messages))
        assert len(messages) == 1
        message = messages[0]
        assert message['request_id'] == '42 is the answer'
