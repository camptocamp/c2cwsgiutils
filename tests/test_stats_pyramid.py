from c2cwsgiutils.stats_pyramid._db_spy import _simplify_sql as simplify_sql   # pylint: disable=W0212


def test_simplify_sql():

    assert simplify_sql("SELECT a FROM xxx WHERE b IN (1, 2, 3)") == \
        "SELECT FROM xxx WHERE b IN (?)"

    assert simplify_sql("SELECT a FROM xxx WHERE b IN (1, 2, 3) AND c=2") == \
        "SELECT FROM xxx WHERE b IN (?) AND c=2"

    assert simplify_sql("SELECT a FROM xxx WHERE b IN (1, 2, 3) AND c IN (d, e)") == \
        "SELECT FROM xxx WHERE b IN (?) AND c IN (?)"

    assert simplify_sql("SELECT a FROM xxx WHERE b IN (1, 2) AND c IN ((d, 1), (e, 2))") == \
        "SELECT FROM xxx WHERE b IN (?) AND c IN (?)"

    assert simplify_sql("SELECT a FROM xxx WHERE b IN (1, ')', 2)") == \
        "SELECT FROM xxx WHERE b IN (?)"
