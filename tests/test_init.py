from unittest.mock import patch

from c2cwsgiutils import get_config_defaults


@patch.dict("c2cwsgiutils.os.environ", {"VARIABLE": "value", "variable": "value"})
def test_get_config_defaults_with_duplicates_in_env() -> None:
    defaults = get_config_defaults()
    assert "value" == defaults["VARIABLE"]  # pylint: disable=W0212
    assert "variable" not in defaults


@patch.dict("c2cwsgiutils.os.environ", {"VARIABLE": "value%"})
def test_get_config_defaults_with_per_cent() -> None:
    defaults = get_config_defaults()
    assert "value%%" == defaults["VARIABLE"]  # pylint: disable=W0212
