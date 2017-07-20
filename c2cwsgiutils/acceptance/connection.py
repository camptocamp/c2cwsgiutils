import re
from lxml import etree
import requests


COLON_SPLIT_RE = re.compile(r'\s*,\s*')


class Connection:
    def __init__(self, base_url, origin):
        self.base_url = base_url
        self.session = requests.session()
        self.origin = origin

    def get(self, url, expected_status=200, params=None, headers=None, cors=True, cache_allowed=False):
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, params=params,
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r.text

    def get_raw(self, url, expected_status=200, params=None, headers=None, cors=True, cache_allowed=False):
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, params=params,
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r

    def get_json(self, url, expected_status=200, params=None, headers=None, cors=True, cache_allowed=False):
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, params=params,
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def get_xml(self, url, schema=None, expected_status=200, headers=None, params=None, cors=True,
                cache_allowed=False):
        """
        get the given URL (relative to the root of API).
        """
        with self.session.get(self.base_url + url, headers=self._merge_headers(headers, cors), params=params,
                              stream=True) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            r.raw.decode_content = True
            doc = etree.parse(r.raw)
            if schema is not None:
                with open(schema, 'r') as schema_file:
                    xml_schema = etree.XMLSchema(etree.parse(schema_file))
                xml_schema.assertValid(doc)
            return doc

    def post_json(self, url, data=None, json=None, expected_status=200, headers=None, cors=True,
                  cache_allowed=False):
        """
        POST the given URL (relative to the root of API).
        """
        with self.session.post(self.base_url + url, data=data, json=json,
                               headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed=cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def post_files(self, url, data=None, files=None, expected_status=200, headers=None, cors=True,
                   cache_allowed=False):
        """
        POST files to the the given URL (relative to the root of API).
        """
        with self.session.post(self.base_url + url, data=data, files=files,
                               headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def post(self, url, data=None, expected_status=200, headers=None, cors=True, cache_allowed=False):
        """
        POST the given URL (relative to the root of API).
        """
        with self.session.post(self.base_url + url, headers=self._merge_headers(headers, cors),
                               data=data) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r.text

    def put_json(self, url, json=None, expected_status=200, headers=None, cors=True, cache_allowed=False):
        """
        POST the given URL (relative to the root of API).
        """
        with self.session.put(self.base_url + url, json=json,
                              headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r.json()

    def delete(self, url, expected_status=204, headers=None, cors=True, cache_allowed=False):
        """
        DELETE the given URL (relative to the root of API).
        """
        with self.session.delete(self.base_url + url, headers=self._merge_headers(headers, cors)) as r:
            check_response(r, expected_status, cache_allowed)
            self._check_cors(cors, r)
            return r

    def _cors_headers(self, cors):
        if cors:
            return {
                "Origin": self.origin
            }
        else:
            return {}

    def _check_cors(self, cors, r):
        if cors:

            assert r.headers["Access-Control-Allow-Origin"] == \
                   self.origin if 'Access-Control-Allow-Credentials' in r.headers else '*'

    def _merge_headers(self, headers, cors):
        merged = dict(headers) if headers is not None else {}
        merged.update(self.session.headers)
        merged.update(self._cors_headers(cors))
        return merged


def check_response(r, expected_status=200, cache_allowed=True):
    if isinstance(expected_status, tuple):
        assert r.status_code in expected_status, "status=%d\n%s" % (r.status_code, r.text)
    else:
        assert r.status_code == expected_status, "status=%d\n%s" % (r.status_code, r.text)

    if not cache_allowed:
        # Cache is the root of all evil. Must never be enabled
        assert 'Cache-Control' in r.headers
        cache_control = COLON_SPLIT_RE.split(r.headers['Cache-Control'])
        assert 'no-cache' in cache_control
