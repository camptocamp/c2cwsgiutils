import re
from collections.abc import Mapping, MutableMapping
from enum import Enum
from typing import Any, Optional, Union

import requests

COLON_SPLIT_RE = re.compile(r"\s*,\s*")


class CacheExpected(Enum):
    """The cache expiry."""

    NO = 0  # no-cache
    YES = 1  # max-age>0
    DONT_CARE = 2


class Connection:
    """The connection."""

    def __init__(self, base_url: str, origin: str) -> None:
        self.base_url = base_url
        if not self.base_url.endswith("/"):
            self.base_url += "/"
        self.session = requests.session()
        self.origin = origin

    def get(
        self,
        url: str,
        expected_status: int = 200,
        cors: bool = True,
        headers: Optional[Mapping[str, str]] = None,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Optional[str]:
        """Get the given URL (relative to the root of API)."""
        with self.session.get(self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs) as r:
            check_response(r, expected_status, cache_expected=cache_expected)
            self._check_cors(cors, r)
            return None if r.status_code == 204 else r.text

    def get_raw(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> requests.Response:
        """Get the given URL (relative to the root of API)."""
        with self.session.get(self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs) as r:
            check_response(r, expected_status, cache_expected=cache_expected)
            self._check_cors(cors, r)
            return r

    def get_json(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Any:
        """Get the given URL (relative to the root of API)."""
        with self.session.get(self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs) as r:
            check_response(r, expected_status, cache_expected=cache_expected)
            self._check_cors(cors, r)
            return _get_json(r)

    def get_xml(
        self,
        url: str,
        schema: Optional[str] = None,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Any:
        """Get the given URL (relative to the root of API)."""
        from lxml import etree  # nosec # pylint: disable=import-outside-toplevel

        with self.session.get(
            self.base_url + url,
            headers=self._merge_headers(headers, cors),
            stream=True,
            **kwargs,
        ) as r:
            check_response(r, expected_status, cache_expected=cache_expected)
            self._check_cors(cors, r)
            r.raw.decode_content = True
            doc = etree.parse(r.raw)  # nosec
            if schema is not None:
                with open(schema, encoding="utf-8") as schema_file:
                    xml_schema = etree.XMLSchema(etree.parse(schema_file))  # nosec
                xml_schema.assertValid(doc)
            return doc

    def post_json(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Any:
        """POST the given URL (relative to the root of API)."""
        with self.session.post(
            self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs
        ) as r:
            check_response(r, expected_status, cache_expected=cache_expected)
            self._check_cors(cors, r)
            return _get_json(r)

    def post_files(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Any:
        """POST files to the the given URL (relative to the root of API)."""
        with self.session.post(
            self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs
        ) as r:
            check_response(r, expected_status, cache_expected)
            self._check_cors(cors, r)
            return _get_json(r)

    def post(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Optional[str]:
        """POST the given URL (relative to the root of API)."""
        with self.session.post(
            self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs
        ) as r:
            check_response(r, expected_status, cache_expected)
            self._check_cors(cors, r)
            return None if r.status_code == 204 else r.text

    def put_json(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Any:
        """PUT the given URL (relative to the root of API)."""
        with self.session.put(self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs) as r:
            check_response(r, expected_status, cache_expected)
            self._check_cors(cors, r)
            return _get_json(r)

    def patch_json(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> Any:
        """PATCH the given URL (relative to the root of API)."""
        with self.session.patch(
            self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs
        ) as r:
            check_response(r, expected_status, cache_expected)
            self._check_cors(cors, r)
            return _get_json(r)

    def delete(
        self,
        url: str,
        expected_status: int = 204,
        headers: Optional[Mapping[str, str]] = None,
        cors: bool = True,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> requests.Response:
        """DELETE the given URL (relative to the root of API)."""
        with self.session.delete(
            self.base_url + url, headers=self._merge_headers(headers, cors), **kwargs
        ) as r:
            check_response(r, expected_status, cache_expected)
            self._check_cors(cors, r)
            return r

    def options(
        self,
        url: str,
        expected_status: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        cache_expected: CacheExpected = CacheExpected.NO,
        **kwargs: Any,
    ) -> requests.Response:
        """Get the given URL (relative to the root of API)."""
        with self.session.options(
            self.base_url + url, headers=self._merge_headers(headers, False), **kwargs
        ) as r:
            check_response(r, expected_status, cache_expected=cache_expected)
            return r

    def _cors_headers(self, cors: bool) -> Mapping[str, str]:
        if cors:
            return {"Origin": self.origin}
        else:
            return {}

    def _check_cors(self, cors: bool, r: requests.Response) -> None:
        if cors:
            if r.headers.get("Access-Control-Allow-Credentials", "false") == "true":
                assert r.headers["Access-Control-Allow-Origin"] == self.origin
            else:
                assert r.headers["Access-Control-Allow-Origin"] == "*"

    def _merge_headers(
        self, headers: Optional[Mapping[str, Union[str, bytes]]], cors: bool
    ) -> MutableMapping[str, Union[str, bytes]]:
        merged = dict(headers) if headers is not None else {}
        if self.session.headers is not None:
            merged.update(self.session.headers)
        merged.update(self._cors_headers(cors))
        return merged


def check_response(
    r: requests.Response,
    expected_status: int = 200,
    cache_expected: CacheExpected = CacheExpected.DONT_CARE,
) -> None:
    """Check the response."""
    if isinstance(expected_status, tuple):
        assert r.status_code in expected_status, f"status={r.status_code:d}\n{r.text}"
    else:
        assert r.status_code == expected_status, f"status={r.status_code:d}\n{r.text}"

    if cache_expected == CacheExpected.NO:
        # Cache is the root of all evil. Must never be enabled
        assert "Cache-Control" in r.headers
        cache_control = COLON_SPLIT_RE.split(r.headers["Cache-Control"])
        assert "no-cache" in cache_control
    elif cache_expected == CacheExpected.YES:
        assert "Cache-Control" in r.headers
        assert "max-age=" in r.headers["Cache-Control"]
        assert "max-age=0" not in r.headers["Cache-Control"]
        assert "no-cache" not in r.headers["Cache-Control"]


def _get_json(r: requests.Response) -> Any:
    if r.status_code == 204:
        return None
    else:
        content_type = r.headers["Content-Type"].split(";")[0]
        assert content_type == "application/json" or content_type.endswith(
            "+json"
        ), f"{r.status_code}, {content_type}, {r.text}"
        return r.json()
