import logging
import json
import random
import string
import threading
import time

from c2cwsgiutils._broadcast import utils, interface

LOG = logging.getLogger(__name__)


class RedisBroadcaster(interface.BaseBroadcaster):
    """
    Implement broadcasting messages using Redis
    """
    def __init__(self, redis_url, broadcast_prefix):
        self._broadcast_prefix = broadcast_prefix
        import redis
        self._connection = redis.StrictRedis.from_url(redis_url)
        self._pub_sub = self._connection.pubsub(ignore_subscribe_messages=True)

        # need to be subscribed to something for the thread to stay alive
        self._pub_sub.subscribe(**{self._get_channel('c2c_dummy'): lambda message: None})
        self._thread = self._pub_sub.run_in_thread(sleep_time=1, daemon=True)
        self._thread.name = "c2c_broadcast_listener"

    def _get_channel(self, channel):
        return self._broadcast_prefix + channel

    def subscribe(self, channel, callback):
        def wrapper(message):
            LOG.debug('Received a broadcast on %s: %s', message['channel'], repr(message['data']))
            data = json.loads(message['data'])
            try:
                response = callback(**data['params'])
            except Exception as e:
                LOG.error("Failed handling a broadcast message", exc_info=True)
                response = dict(status=500, message=str(e))
            answer_channel = data.get('answer_channel')
            if answer_channel is not None:
                LOG.debug("Sending broadcast answer on %s", answer_channel)
                self._connection.publish(answer_channel, json.dumps(utils.add_host_info(response)))

        self._pub_sub.subscribe(**{self._get_channel(channel): wrapper})

    def unsubscribe(self, channel):
        self._pub_sub.unsubscribe(self._get_channel(channel))

    def broadcast(self, channel, params, expect_answers, timeout):
        answer_channel = None
        cond = None
        answers = []
        actual_channel = self._get_channel(channel)
        assert self._thread.is_alive()
        message = {'params': params}

        if expect_answers:
            cond = threading.Condition()

            def callback(message):
                LOG.debug('Received a broadcast answer on %s', message['channel'])
                with cond:
                    answers.append(json.loads(message['data']))
                    cond.notify()

            answer_channel = actual_channel + \
                ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            LOG.debug('Subscribing for broadcast answers on %s', answer_channel)
            self._pub_sub.subscribe(**{answer_channel: callback})
            message['answer_channel'] = answer_channel

        try:
            LOG.debug("Sending a broadcast on %s", actual_channel)
            nb_received = self._connection.publish(actual_channel, json.dumps(message))
            LOG.debug('Broadcast on %s sent to %d listeners', actual_channel, nb_received)

            if expect_answers:
                timeout_time = time.monotonic() + timeout
                with cond:
                    while len(answers) < nb_received:
                        to_wait = timeout_time - time.monotonic()
                        if to_wait <= 0.0:
                            LOG.warning("timeout waiting for answers on %s", answer_channel)
                            while len(answers) < nb_received:
                                answers.append(None)
                            return answers
                        cond.wait(to_wait)
                return answers
            else:
                return None
        finally:
            if answer_channel is not None:
                self._pub_sub.unsubscribe(answer_channel)
