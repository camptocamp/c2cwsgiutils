import json
import logging
import re

_LOG = logging.getLogger(__name__)


def test_logs_request_id(app2_connection, composition):
    app2_connection.get_json("ping", headers={"X-Request-ID": "42 is the answer"})
    logs = composition.dc(["logs", "app2"]).split("\n")
    print("Got logs: " + repr(logs))
    logs = [l for l in logs if re.search(r"\|.{4} \{", l)]
    logs = [json.loads(l[l.index("{") :]) for l in logs]
    logs = [l for l in logs if l["logger_name"] == "c2cwsgiutils_app.services.ping"]
    assert logs[-1]["request_id"] == "42 is the answer"
