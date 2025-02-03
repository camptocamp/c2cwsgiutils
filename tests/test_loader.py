from unittest.mock import mock_open, patch

from pyramid.scripts.common import get_config_loader


@patch(
    "paste.deploy.loadwsgi.open",
    mock_open(
        read_data="""
[app:main]
variable = %(VARIABLE)s
"""
    ),
)
@patch.dict("c2cwsgiutils.os.environ", {"VARIABLE": "value"})
def test_loader_success() -> None:
    loader = get_config_loader("c2c:///app/production.ini")
    assert repr(loader) == 'c2cwsgiutils.loader.Loader(uri="c2c:///app/production.ini")'
    assert loader._get_defaults()["VARIABLE"] == "value"  # pylint: disable=W0212
    assert loader.get_settings("app:main")["variable"] == "value"
