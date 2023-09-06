import os

import pytest

from c2cwsgiutils.acceptance import image


@pytest.mark.parametrize(
    "expected_file_name,width,height,headers,media",
    [
        pytest.param("c2c.expected.png", 650, 500, {}, [{"name": "prefers-color-scheme", "value": "light"}]),
        pytest.param(
            "c2c-auth.expected.png",
            650,
            2000,
            {"X-API-Key": "changeme"},
            [{"name": "prefers-color-scheme", "value": "light"}],
        ),
        pytest.param(
            "c2c-auth-dark.expected.png",
            650,
            2000,
            {"X-API-Key": "changeme"},
            [
                {"name": "prefers-color-scheme", "value": "dark"},
            ],
        ),
    ],
)
def test_screenshot(app_connection, expected_file_name, width, height, headers, media):
    image.check_screenshot(
        app_connection.base_url + "c2c",
        headers=headers,
        media=media,
        width=width,
        height=height,
        result_folder="results",
        expected_filename=os.path.join(os.path.dirname(__file__), expected_file_name),
    )
