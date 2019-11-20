from c2cwsgiutils import metrics


class Provider(metrics.Provider):
    def get_data(self):
        return [
            ({'key': 'value'}, 10),
            ({'key2': 'value2'}, 11.5),
        ]


def test_metrics():
    try:
        provider = Provider('test', 'help')
        provider.extend = False
        metrics.PROVIDERS_ = []
        metrics.add_provider(provider)
        assert metrics._metrics() == """# HELP test help
# TYPE test gauge
test{key="value"} 10
test{key2="value2"} 11.5"""
    finally:
        metrics.PROVIDERS_ = []
