import pytest
from c2cwsgiutils.prometheus import PushgatewayGroupPublisher


def test_pushgateway_group_publisher():
    publisher = PushgatewayGroupPublisher("http://example.com/", "test")
    publisher.add("metric1", 12)
    publisher.add("metric2", 13, metric_labels={"toto": "TOTO", "tutu": "TUTU"})
    publisher.add("metric2", 14, metric_labels={"toto": "TOTO", "tutu": "TITI"})
    with pytest.raises(ValueError):
        publisher.add("metric1", 12, metric_type="counter")

    assert (
        str(publisher) == "http://example.com/metrics/job/test ->\n"
        "# TYPE metric1 gauge\n"
        "metric1 12\n"
        "# TYPE metric2 gauge\n"
        'metric2{toto="TOTO", tutu="TUTU"} 13\n'
        'metric2{toto="TOTO", tutu="TITI"} 14\n'
    )


def test_pushgateway_group_publisher_with_labels():
    publisher = PushgatewayGroupPublisher("http://example.com/", "test", labels={"titi": "TITI"})
    publisher.add("metric1", 12)
    publisher.add("metric2", 13, metric_labels={"toto": "TOTO", "tutu": "TUTU"})
    publisher.add("metric2", 14, metric_labels={"toto": "TOTO", "tutu": "TITI"})

    assert (
        str(publisher) == "http://example.com/metrics/job/test ->\n"
        "# TYPE metric1 gauge\n"
        'metric1{titi="TITI"} 12\n'
        "# TYPE metric2 gauge\n"
        'metric2{titi="TITI", toto="TOTO", tutu="TUTU"} 13\n'
        'metric2{titi="TITI", toto="TOTO", tutu="TITI"} 14\n'
    )
