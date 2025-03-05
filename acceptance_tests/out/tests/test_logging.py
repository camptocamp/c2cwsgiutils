import json
import logging
import re

_LOG = logging.getLogger(__name__)


def test_logs_request_id(app2_connection, composition):
    app2_connection.get_json("ping", headers={"X-Request-ID": "42 is the answer"})
    logs = composition.dc(["logs", "app2"]).split("\n")
    print("Got logs: " + repr(logs))
    logs = [line for line in logs if re.search(r"\| \{", line)]
    logs = [json.loads(line[line.index("{") :]) for line in logs]
    logs = [line for line in logs if line["logger_name"] == "c2cwsgiutils_app.services.ping"]
    assert logs[-1]["request_id"] == "42 is the answer"
