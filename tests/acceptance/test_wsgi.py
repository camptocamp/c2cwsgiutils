from c2cwsgiutils.wsgi import _escape_variables


def test_escape_variables():
    assert {
        'TOTO': 'TITI',
        'TUTU': 'T%%T%%',
        'TATA': '',
    } == _escape_variables({
        'TOTO': 'TITI',
        'TUTU': 'T%T%',
        'TATA': ''
    })
