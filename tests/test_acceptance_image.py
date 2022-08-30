import os

import pytest

from c2cwsgiutils.acceptance.image import check_image_file


def test_good():
    image = os.path.join(os.path.dirname(__file__), "test.expected.png")
    check_image_file("/results", image, os.path.join(os.path.dirname(__file__), "test.expected.png"))


def test_wrong():
    image = os.path.join(os.path.dirname(__file__), "test.wrong.png")
    with pytest.raises(AssertionError):
        check_image_file("/results", image, os.path.join(os.path.dirname(__file__), "test.expected.png"))
    check_image_file(
        "/results",
        "/results/test.diff.png",
        os.path.join(os.path.dirname(__file__), "test.diff.expected.png"),
    )
