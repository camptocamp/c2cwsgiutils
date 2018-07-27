import logging
import json
import random
import string
import threading
from typing import Callable, Optional, Mapping, Any  # noqa  # pylint: disable=unused-import
import time

from c2cwsgiutils.broadcast import utils, interface, local

LOG = logging.getLogger(__name__)


class RedisBroadcaster(interface.BaseBroadcaster):
    """
    Implement broadcasting messages using Redis
    """
    def __init__(self, redis_url: str, broadcast_prefix: str) -> None:
        import redis
        from c2cwsgiutils import redis_utils
        self._broadcast_prefix = broadcast_prefix
        self._connection = redis.StrictRedis.from_url(redis_url)
        self._pub_sub = self._connection.pubsub(ignore_subscribe_messages=True)

        # need to be subscribed to something for the thread to stay alive
        self._pub_sub.subscribe(**{self._get_channel('c2c_dummy'): lambda message: None})
        self._thread = redis_utils.PubSubWorkerThread(self._pub_sub, name="c2c_broadcast_listener")
        self._thread.start()

    def _get_channel(self, channel: str) -> str:
        return self._broadcast_prefix + channel

    def subscribe(self, channel: str, callback: Callable) -> None:
        def wrapper(message: Mapping[str, Any]) -> None:
            LOG.debug('Received a broadcast on %s: %s', message['channel'], repr(message['data']))
            data = json.loads(message['data'].decode('utf-8'))
            try:
                response = callback(**data['params'])
            except Exception as e:  # pragma: no cover
                LOG.error("Failed handling a broadcast message", exc_info=True)
                response = dict(status=500, message=str(e))
            answer_channel = data.get('answer_channel')
            if answer_channel is not None:
                LOG.debug("Sending broadcast answer on %s", answer_channel)
                self._connection.publish(answer_channel, json.dumps(utils.add_host_info(response)))

        LOG.debug("Subscribing %s.%s to %s", callback.__module__, callback.__name__, channel)
        self._pub_sub.subscribe(**{self._get_channel(channel): wrapper})

    def unsubscribe(self, channel: str) -> None:
        LOG.debug("Unsubscribing from %s")
        self._pub_sub.unsubscribe(self._get_channel(channel))

    def broadcast(self, channel: str, params: Mapping[str, Any], expect_answers: bool,
                  timeout: float) -> Optional[list]:
        if expect_answers:
            return self._broadcast_with_answer(channel, params, timeout)
        else:
            self._broadcast(channel, {'params': params})
            return None

    def _broadcast_with_answer(self, channel: str, params: Optional[Mapping[str, Any]],
                               timeout: float) -> list:
        cond = threading.Condition()
        answers = []
        assert self._thread.is_alive()

        def callback(msg: Mapping[str, Any]) -> None:
            LOG.debug('Received a broadcast answer on %s', msg['channel'])
            with cond:
                answers.append(json.loads(msg['data'].decode('utf-8')))
                cond.notify()

        answer_channel = self._get_channel(channel) + \
            ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        LOG.debug('Subscribing for broadcast answers on %s', answer_channel)
        self._pub_sub.subscribe(**{answer_channel: callback})
        message = {
            'params': params,
            'answer_channel': answer_channel
        }

        try:
            nb_received = self._broadcast(channel, message)

            timeout_time = time.monotonic() + timeout
            with cond:
                while len(answers) < nb_received:
                    to_wait = timeout_time - time.monotonic()
                    if to_wait <= 0.0:  # pragma: no cover
                        LOG.warning("timeout waiting for answers on %s", answer_channel)
                        while len(answers) < nb_received:
                            answers.append(None)
                        return answers
                    cond.wait(to_wait)
            return answers
        finally:
            self._pub_sub.unsubscribe(answer_channel)

    def _broadcast(self, channel: str, message: Mapping[str, Any]) -> int:
        actual_channel = self._get_channel(channel)
        LOG.debug("Sending a broadcast on %s", actual_channel)
        nb_received = self._connection.publish(actual_channel, json.dumps(message))
        LOG.debug('Broadcast on %s sent to %d listeners', actual_channel, nb_received)
        return nb_received

    def copy_local_subscriptions(self, prev_broadcaster: local.LocalBroadcaster) -> None:
        for channel, callback in prev_broadcaster.get_subscribers().items():
            self.subscribe(channel, callback)
