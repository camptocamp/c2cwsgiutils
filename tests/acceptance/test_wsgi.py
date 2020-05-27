from c2cwsgiutils.wsgi import _escape_variables as escape_variables  # pylint: disable=W0212


def test_escape_variables():
    assert {"TOTO": "TITI", "TUTU": "T%%T%%", "TATA": ""} == escape_variables(
        {"TOTO": "TITI", "TUTU": "T%T%", "TATA": ""}
    )
