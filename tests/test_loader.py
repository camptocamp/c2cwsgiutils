import pytest
from unittest.mock import patch, mock_open
from pyramid.scripts.common import get_config_loader


@pytest.mark.skipif(True, reason="No more working in CI")
@patch('paste.deploy.loadwsgi.open', mock_open(read_data='''
[app:main]
variable = %(VARIABLE)s
'''))
@patch.dict('c2cwsgiutils.loader.os.environ', {'VARIABLE': 'value'})
def test_loader():
    loader = get_config_loader('c2c:///app/production.ini')
    assert 'c2cwsgiutils.loader.Loader(uri="c2c:///app/production.ini")' == repr(loader)
    assert 'value' == loader._get_defaults()['VARIABLE']  # pylint: disable=W0212
    assert 'value' == loader.get_settings('app:main')['variable']
