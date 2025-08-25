from pathlib import Path

import pytest

from c2cwsgiutils.acceptance.image import check_image_file


def test_good():
    image = Path(__file__).parent / "test.expected.png"
    check_image_file("/results", image, Path(__file__).parent / "test.expected.png")


def test_wrong():
    image = Path(__file__).parent / "test.wrong.png"
    with pytest.raises(AssertionError):
        check_image_file(
            "/results",
            image,
            Path(__file__).parent / "test.expected.png",
            use_mask=False,
        )
    check_image_file(
        "/results",
        "/results/test.diff.png",
        Path(__file__).parent / "test.diff.expected.png",
    )


def test_mask():
    image = Path(__file__).parent / "test.wrong.png"
    check_image_file("/results", image, Path(__file__).parent / "test.expected.png")


def test_mask_1_bit():
    image = Path(__file__).parent / "test-alpha-wrong.png"
    check_image_file("/results", image, Path(__file__).parent / "test-1-bit.expected.png")
