import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from upload_confluence_v2 import upload_to_confluence


class FakeConfluence:
    def __init__(self, versions):
        self.url = "https://confluence.example"
        self.versions = list(versions)
        self.update_kwargs = None

    def get_page_by_id(self, page_id, expand=None):
        version = self.versions.pop(0)
        return {
            "id": page_id,
            "title": "Test Page",
            "version": {"number": version},
            "body": {"storage": {"value": "<p>body</p>"}},
            "_links": {"webui": f"/pages/{page_id}"},
        }

    def update_page(self, **kwargs):
        self.update_kwargs = kwargs
        return {
            "id": kwargs["page_id"],
            "title": kwargs["title"],
            "version": {"number": 999},
            "_links": {"webui": f"/pages/{kwargs['page_id']}"},
        }


class UploadVerificationTests(unittest.TestCase):
    def test_update_requires_version_bump(self):
        confluence = FakeConfluence([10, 10])

        with self.assertRaisesRegex(ValueError, "version stayed at 10"):
            upload_to_confluence(
                confluence=confluence,
                page_id="123",
                title="Test Page",
                storage_html="<p>new</p>",
                attachments=[],
            )

    def test_update_verifies_read_back_version_and_forces_update(self):
        confluence = FakeConfluence([10, 11])

        result = upload_to_confluence(
            confluence=confluence,
            page_id="123",
            title="Test Page",
            storage_html="<p>new</p>",
            attachments=[],
        )

        self.assertEqual(result["version"], 11)
        self.assertTrue(confluence.update_kwargs["always_update"])


if __name__ == "__main__":
    unittest.main()
