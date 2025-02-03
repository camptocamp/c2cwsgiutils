from c2cwsgiutils.acceptance import utils


def test_approx():
    assert utils.approx({"a": 5.6, "b": [4.3], "c": {"d": 2.3}}, abs=0.1) == {
        "a": 5.61,
        "b": [4.32],
        "c": {"d": 2.33},
    }

    assert utils.approx({"a": 5.6, "b": [4.3], "c": {"d": 2.3}}, abs=0.1) != {
        "a": 5.61,
        "b": [4.32],
        "c": {"d": 2.5},
    }

    assert utils.approx(3.15, abs=0.02) == 3.14
