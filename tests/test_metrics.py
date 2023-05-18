from time import sleep

from c2cwsgiutils import metrics


class Provider(metrics.Provider):
    def get_data(self):
        return [
            ({"key": "value"}, 10),
            ({"key2": "value2"}, 11.5),
        ]


def test_metrics():
    try:
        provider = Provider("test", "help")
        provider.extend = False
        metrics.PROVIDERS_ = []
        metrics.add_provider(provider)
        assert (
            metrics._metrics()
            == """# HELP test help
# TYPE test gauge
test{key="value"} 10
test{key2="value2"} 11.5"""
        )
    finally:
        metrics.PROVIDERS_ = []


def test_gauge():
    gauge = metrics.Gauge("test", "help")
    value1 = gauge.get_value({"key": "value1"})
    value2 = gauge.get_value({"key": "value1"})
    assert value1.get_value() == 0
    value1.set_value(10)
    value2.set_value(20)
    value1 = gauge.get_value({"key": "value1"})
    value2 = gauge.get_value({"key": "value1"})
    assert value1.get_value() == 10
    assert value2.get_value() == 20


def test_count_with():
    counter = metrics.Counter("test", "help")
    counter_value = counter.get_value({})
    assert counter_value.get_value() == 0
    with counter_value.count():
        pass
    assert counter_value.get_value() == 1


def test_time_with():
    counter = metrics.Counter("test", "help")
    counter_value = counter.get_value({})
    assert counter_value.get_value() == 0
    with counter_value.time():
        sleep(1)
    assert counter_value.get_value() == 1


def test_count_decorator():
    counter = metrics.Counter("test", "help")
    counter_value = counter.get_value({})

    @counter_value.count()
    def test():
        pass

    assert counter_value.get_value() == 0
    test()
    assert counter_value.get_value() == 1


def test_time_decorator():
    counter = metrics.Counter("test", "help")
    counter_value = counter.get_value({})

    @counter_value.time()
    def test():
        pass

    assert counter_value.get_value() == 0
    test()
    assert counter_value.get_value() == 1
