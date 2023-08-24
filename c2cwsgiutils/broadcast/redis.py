import json
import logging
import random
import string
import threading
import time
from collections.abc import Mapping
from typing import Any, Callable, Optional

import redis

from c2cwsgiutils.broadcast import interface, local, utils

LOG = logging.getLogger(__name__)


class RedisBroadcaster(interface.BaseBroadcaster):
    """Implement broadcasting messages using Redis."""

    def __init__(
        self,
        broadcast_prefix: str,
        master: "redis.client.Redis[str]",
        slave: "redis.client.Redis[str]",
    ) -> None:
        from c2cwsgiutils import redis_utils

        self._master = master
        self._slave = slave
        self._broadcast_prefix = broadcast_prefix

        self._pub_sub = self._master.pubsub(ignore_subscribe_messages=True)

        # Need to be subscribed to something for the thread to stay alive
        self._pub_sub.subscribe(**{self._get_channel("c2c_dummy"): lambda message: None})
        self._thread = redis_utils.PubSubWorkerThread(self._pub_sub, name="c2c_broadcast_listener")
        self._thread.start()

    def _get_channel(self, channel: str) -> str:
        return self._broadcast_prefix + channel

    def subscribe(self, channel: str, callback: Callable[..., Any]) -> None:
        def wrapper(message: Mapping[str, Any]) -> None:
            LOG.debug("Received a broadcast on %s: %s", message["channel"], repr(message["data"]))
            data = json.loads(message["data"])
            try:
                response = callback(**data["params"])
            except Exception as e:  # pragma: no cover  # pylint: disable=broad-except
                LOG.error("Failed handling a broadcast message", exc_info=True)
                response = {"status": 500, "message": str(e)}
            answer_channel = data.get("answer_channel")
            if answer_channel is not None:
                LOG.debug("Sending broadcast answer on %s", answer_channel)
                self._master.publish(answer_channel, json.dumps(utils.add_host_info(response)))

        actual_channel = self._get_channel(channel)
        LOG.debug("Subscribing %s.%s to %s", callback.__module__, callback.__name__, actual_channel)
        self._pub_sub.subscribe(**{actual_channel: wrapper})

    def unsubscribe(self, channel: str) -> None:
        LOG.debug("Unsubscribing from %s")
        actual_channel = self._get_channel(channel)
        self._pub_sub.unsubscribe(actual_channel)

    def broadcast(
        self, channel: str, params: Mapping[str, Any], expect_answers: bool, timeout: float
    ) -> Optional[list[Any]]:
        if expect_answers:
            return self._broadcast_with_answer(channel, params, timeout)
        else:
            self._broadcast(channel, {"params": params})
            return None

    def _broadcast_with_answer(
        self, channel: str, params: Optional[Mapping[str, Any]], timeout: float
    ) -> list[Any]:
        cond = threading.Condition()
        answers = []
        assert self._thread.is_alive()

        def callback(msg: Mapping[str, Any]) -> None:
            LOG.debug("Received a broadcast answer on %s", msg["channel"])
            with cond:
                answers.append(json.loads(msg["data"]))
                cond.notify()

        answer_channel = self._get_channel(channel) + "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(10)  # nosec
        )
        LOG.debug("Subscribing for broadcast answers on %s", answer_channel)
        self._pub_sub.subscribe(**{answer_channel: callback})
        message = {"params": params, "answer_channel": answer_channel}

        try:
            nb_received = self._broadcast(channel, message)

            timeout_time = time.perf_counter() + timeout
            with cond:
                while len(answers) < nb_received:
                    to_wait = timeout_time - time.perf_counter()
                    if to_wait <= 0.0:  # pragma: no cover
                        LOG.warning(
                            "timeout waiting for %d/%d answers on %s",
                            len(answers),
                            nb_received,
                            answer_channel,
                        )
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
        nb_received = self._master.publish(actual_channel, json.dumps(message))
        LOG.debug("Broadcast on %s sent to %d listeners", actual_channel, nb_received)
        return nb_received

    def copy_local_subscriptions(self, prev_broadcaster: local.LocalBroadcaster) -> None:
        for channel, callback in prev_broadcaster.get_subscribers().items():
            self.subscribe(channel, callback)
