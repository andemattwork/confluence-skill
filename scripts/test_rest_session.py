import os
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from confluence_auth import get_rest_session

_KEYS = [
    "CONFLUENCE_URL", "CONFLUENCE_USERNAME", "CONFLUENCE_PERSONAL_TOKEN",
    "CONFLUENCE_API_TOKEN", "CONFLUENCE_PASSWORD", "CONFLUENCE_AUTH_TYPE",
    "CONFLUENCE_CONTEXT_PATH",
]


class RestSessionTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in _KEYS}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_dc_bearer_with_context_path(self):
        os.environ["CONFLUENCE_URL"] = "https://confluence.example.com"
        os.environ["CONFLUENCE_USERNAME"] = "svc"
        os.environ["CONFLUENCE_PERSONAL_TOKEN"] = "tok123"
        os.environ["CONFLUENCE_AUTH_TYPE"] = "bearer"
        os.environ["CONFLUENCE_CONTEXT_PATH"] = "wiki"

        session, api_base, web_base = get_rest_session()
        self.assertEqual(web_base, "https://confluence.example.com/wiki")
        self.assertEqual(api_base, "https://confluence.example.com/wiki/rest/api")
        self.assertEqual(session.headers.get("Authorization"), "Bearer tok123")

    def test_no_double_append_when_url_has_context_path(self):
        os.environ["CONFLUENCE_URL"] = "https://confluence.example.com/wiki"
        os.environ["CONFLUENCE_USERNAME"] = "svc"
        os.environ["CONFLUENCE_PERSONAL_TOKEN"] = "tok123"
        os.environ["CONFLUENCE_CONTEXT_PATH"] = "wiki"

        _, api_base, web_base = get_rest_session()
        self.assertEqual(web_base, "https://confluence.example.com/wiki")
        self.assertEqual(api_base, "https://confluence.example.com/wiki/rest/api")

    def test_basic_auth(self):
        os.environ["CONFLUENCE_URL"] = "https://confluence.example.com"
        os.environ["CONFLUENCE_USERNAME"] = "user@example.com"
        os.environ["CONFLUENCE_API_TOKEN"] = "apitok"
        os.environ["CONFLUENCE_AUTH_TYPE"] = "basic"

        session, api_base, _ = get_rest_session()
        self.assertEqual(api_base, "https://confluence.example.com/rest/api")
        self.assertEqual(session.auth, ("user@example.com", "apitok"))

    def test_cloud_defaults_context_path_to_wiki(self):
        os.environ["CONFLUENCE_URL"] = "https://acme.atlassian.net"
        os.environ["CONFLUENCE_USERNAME"] = "user@example.com"
        os.environ["CONFLUENCE_API_TOKEN"] = "apitok"

        _, api_base, _ = get_rest_session()
        self.assertEqual(api_base, "https://acme.atlassian.net/wiki/rest/api")

    def test_bearer_pat_without_username(self):
        # DC PAT auth has no username; discovery must still succeed.
        os.environ["CONFLUENCE_URL"] = "https://confluence.example.com"
        os.environ["CONFLUENCE_PERSONAL_TOKEN"] = "pat123"
        os.environ["CONFLUENCE_AUTH_TYPE"] = "bearer"
        os.environ["CONFLUENCE_CONTEXT_PATH"] = "wiki"

        session, api_base, _ = get_rest_session()
        self.assertEqual(api_base, "https://confluence.example.com/wiki/rest/api")
        self.assertEqual(session.headers.get("Authorization"), "Bearer pat123")


if __name__ == "__main__":
    unittest.main()
