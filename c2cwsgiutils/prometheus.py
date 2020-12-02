"""
Implement parts of the Prometheus Pushgateway protocol, as defined here:
https://github.com/prometheus/pushgateway
"""
from typing import Any, Mapping, MutableMapping, Optional  # noqa  # pylint: disable=unused-import

import requests

LabelsType = Optional[Mapping[str, Any]]


class PushgatewayGroupPublisher:
    def __init__(
        self, base_url: str, job: str, instance: Optional[str] = None, labels: LabelsType = None
    ) -> None:
        if not base_url.endswith("/"):
            base_url += "/"
        self._url = "%smetrics/job/%s" % (base_url, job)
        if instance is not None:
            self._url += "/instance/" + instance
        self._labels = labels
        self._reset()

    def _merge_labels(self, labels: LabelsType) -> LabelsType:
        if labels is None:
            return self._labels
        elif self._labels is None:
            return labels
        else:
            tmp = dict(self._labels)
            tmp.update(labels)
            return tmp

    def add(
        self,
        metric_name: str,
        metric_value: Any,
        metric_type: str = "gauge",
        metric_labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        if metric_name in self._types:
            if self._types[metric_name] != metric_type:
                raise ValueError("Cannot change the type of a given metric")
        else:
            self._types[metric_name] = metric_type
            self._to_send += "# TYPE %s %s\n" % (metric_name, metric_type)
        self._to_send += metric_name
        labels = self._merge_labels(metric_labels)
        if labels is not None:
            self._to_send += "{" + ", ".join('%s="%s"' % (k, v) for k, v in sorted(labels.items())) + "}"
        self._to_send += " %s\n" % metric_value

    def commit(self) -> None:
        requests.put(self._url, data=self._to_send.encode("utf-8")).raise_for_status()
        self._reset()

    def _reset(self) -> None:
        self._to_send = ""
        self._types: MutableMapping[str, str] = {}

    def __str__(self) -> str:
        return self._url + " ->\n" + self._to_send
