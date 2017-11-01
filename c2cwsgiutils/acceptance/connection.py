import re
from lxml import etree  # nosec
import requests
from typing import Mapping, Any, Optional

COLON_SPLIT_RE = re.compile(r'\s*,\s*')


class Connection:
    def __init__(self, base_url: str, origin: str) -> None:
        self.base_url = base_url
        self.session = requests.session()
        self.origin = origin

    def get(self, url: str, expected_status: int=200, params: Mapping[str, str]=None,
            headers: Mapping[str, str]=None, cors: bool=True, cache_allowed: bool=False) -> str:
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, params=params,  # type: ignore
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r.text

    def get_raw(self, url: str, expected_status: int=200, params: Mapping[str, str]=None,
                headers: Mapping[str, str]=None, cors: bool=True,
                cache_allowed: bool=False)-> requests.Response:
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, params=params,  # type: ignore
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r

    def get_json(self, url: str, expected_status: int=200, params: Mapping[str, str]=None,
                 headers: Mapping[str, str]=None, cors: bool=True, cache_allowed: bool=False) -> Any:
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, params=params,  # type: ignore
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def get_xml(self, url: str, schema: Optional[str]=None, expected_status: int=200,
                params: Mapping[str, str]=None, headers: Mapping[str, str]=None, cors: bool=True,
                cache_allowed: bool=False) -> Any:
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, headers=self._merge_headers(headers, cors),  # type: ignore
                              params=params, stream=True) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            r.raw.decode_content = True
            doc = etree.parse(r.raw)  # nosec
            if schema is not None:
                with open(schema, 'r') as schema_file:
                    xml_schema = etree.XMLSchema(etree.parse(schema_file))  # nosec
                xml_schema.assertValid(doc)
            return doc

    def post_json(self, url: str, data: Any=None, json: Any=None, expected_status: int=200,
                  params: Mapping[str, str]=None, headers: Mapping[str, str]=None, cors: bool=True,
                  cache_allowed: bool=False) -> Any:
        """
        POST the given URL (relative to the root of API).
        """
        with self.session.post(self.base_url + url, data=data, json=json, params=params,   # type: ignore
                               headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def post_files(self, url: str, data: Any=None, files: Optional[Mapping[str, Any]]=None,
                   expected_status: int=200, params: Mapping[str, str]=None, headers: Mapping[str, str]=None,
                   cors: bool=True, cache_allowed: bool=False) -> Any:
        """
        POST files to the the given URL (relative to the root of API).
        """
        with self.session.post(self.base_url + url, data=data, files=files, params=params,  # type: ignore
                               headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def post(self, url: str, data: Any=None, expected_status: int=200, params: Mapping[str, str]=None,
             headers: Mapping[str, str]=None, cors: bool=True, cache_allowed: bool=False) -> str:
        """
        POST the given URL (relative to the root of API).
        """
        with self.session.post(self.base_url + url,  # type: ignore
                               headers=self._merge_headers(headers, cors),
                               data=data, params=params) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r.text

    def put_json(self, url: str, json: Any=None, expected_status: int=200, params: Mapping[str, str]=None,
                 headers: Mapping[str, str]=None, cors: bool=True, cache_allowed: bool=False) -> Any:
        """
        POST the given URL (relative to the root of API).
        """
        with self.session.put(self.base_url + url, json=json, params=params,  # type: ignore
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def delete(self, url: str, expected_status: int=204, params: Mapping[str, str]=None,
               headers: Mapping[str, str]=None, cors: bool=True,
               cache_allowed: bool=False) -> requests.Response:
        """
        DELETE the given URL (relative to the root of API).
        """
        with self.session.delete(self.base_url + url,  # type: ignore
                                 headers=self._merge_headers(headers, cors), params=params) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r

    def _cors_headers(self, cors: bool) -> Mapping[str, str]:
        if cors:
            return {
                "Origin": self.origin
            }
        else:
            return {}

    def _check_cors(self, cors: bool, r: requests.Response) -> None:
        if cors:

            assert r.headers["Access-Control-Allow-Origin"] == \
                   self.origin if 'Access-Control-Allow-Credentials' in r.headers else '*'

    def _merge_headers(self, headers: Optional[Mapping[str, str]], cors: bool) -> Mapping[str, str]:
        merged = dict(headers) if headers is not None else {}
        if self.session.headers is not None:
            merged.update(self.session.headers)
        merged.update(self._cors_headers(cors))
        return merged


def check_response(r: requests.Response, expected_status: int=200, cache_allowed: bool=True) -> None:
    if isinstance(expected_status, tuple):
        assert r.status_code in expected_status, "status=%d\n%s" % (r.status_code, r.text)
    else:
        assert r.status_code == expected_status, "status=%d\n%s" % (r.status_code, r.text)

    if not cache_allowed:
        # Cache is the root of all evil. Must never be enabled
        assert 'Cache-Control' in r.headers
        cache_control = COLON_SPLIT_RE.split(r.headers['Cache-Control'])
        assert 'no-cache' in cache_control
