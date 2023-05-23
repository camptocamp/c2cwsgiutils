"""Start separate HTTP server to provide the Prometheus metrics."""

import os
from typing import cast

from prometheus_client import CollectorRegistry, multiprocess, start_http_server


def start() -> None:
    """Start separate HTTP server to provide the Prometheus metrics."""

    start_http_server(
        int(os.environ.get("PROMETHEUS_PORT", "9090")),
        registry=cast(
            CollectorRegistry,
            multiprocess.MultiProcessCollector(CollectorRegistry()),  # type: ignore[no-untyped-call]
        ),
    )
