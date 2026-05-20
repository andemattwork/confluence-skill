import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import confluence_auth
import download_confluence


class ConfluenceAuthTests(unittest.TestCase):
    def test_credentials_prefer_personal_token_and_default_bearer(self):
        env = {
            "CONFLUENCE_URL": "https://c.example",
            "CONFLUENCE_USERNAME": "user",
            "CONFLUENCE_PERSONAL_TOKEN": "personal",
            "CONFLUENCE_API_TOKEN": "api",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            creds = confluence_auth.get_confluence_credentials()
        self.assertEqual(creds["token"], "personal")
        self.assertEqual(creds["auth_type"], "bearer")

    def test_credentials_allow_basic_auth_type(self):
        env = {
            "CONFLUENCE_URL": "https://c.example",
            "CONFLUENCE_USERNAME": "user",
            "CONFLUENCE_API_TOKEN": "api",
            "CONFLUENCE_AUTH_TYPE": "basic",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            creds = confluence_auth.get_confluence_credentials()
        self.assertEqual(creds["auth_type"], "basic")

    def test_credentials_do_not_read_home_env_files(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(Path, "home", return_value=Path("/tmp/home")), \
                mock.patch.object(confluence_auth, "_find_env_file_in_directory", return_value=None), \
                mock.patch.object(confluence_auth, "_walk_up_for_env_file", return_value=None), \
                mock.patch.object(confluence_auth, "_load_mcp_config", return_value=None), \
                mock.patch.object(confluence_auth, "load_dotenv") as load_dotenv:
            with self.assertRaises(ValueError):
                confluence_auth.get_confluence_credentials()

        load_dotenv.assert_not_called()

    def test_validator_uses_root_rest_api_by_default(self):
        validator = download_confluence.ConfluenceValidator(
            "https://c.example",
            "user",
            "token",
            auth_type="bearer",
        )
        self.assertEqual(validator.api_base, "https://c.example/rest/api")
        self.assertEqual(validator.web_base, "https://c.example")
        self.assertEqual(validator.session.headers.get("Authorization"), "Bearer token")

    def test_validator_allows_wiki_context_path(self):
        validator = download_confluence.ConfluenceValidator(
            "https://c.example/wiki",
            "user",
            "token",
            auth_type="bearer",
            context_path="/wiki",
        )
        self.assertEqual(validator.api_base, "https://c.example/wiki/rest/api")
        self.assertEqual(validator.web_base, "https://c.example/wiki")


if __name__ == "__main__":
    unittest.main()
