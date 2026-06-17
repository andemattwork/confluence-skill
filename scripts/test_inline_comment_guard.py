import unittest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inline_comments import preflight_guard, verify_after_upload


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, body):
        self._body = body

    def get(self, url, params=None):
        if url.endswith("/child/comment"):
            return FakeResp(200, {"results": []})
        return FakeResp(200, {
            "id": "123456789", "title": "Example",
            "version": {"number": 2}, "_links": {"webui": "/x"},
            "body": {"storage": {"value": self._body}},
        })


TWO = ('<ac:inline-comment-marker ac:ref="r1">a</ac:inline-comment-marker>'
       '<ac:inline-comment-marker ac:ref="r2">b</ac:inline-comment-marker>')


class PreflightGuardTests(unittest.TestCase):
    def test_dry_run_reports_and_backs_up_without_blocking(self):
        with tempfile.TemporaryDirectory() as d:
            r = preflight_guard(FakeSession(TWO), "http://api", "123456789",
                                dry_run=True, allow_orphan_comments=False, backup_dir=d)
            self.assertEqual(r["count"], 2)
            self.assertFalse(r["blocked"])
            self.assertTrue(r["backup_path"].exists())

    def test_blocks_when_comments_and_not_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            r = preflight_guard(FakeSession(TWO), "http://api", "123456789",
                                dry_run=False, allow_orphan_comments=False, backup_dir=d)
            self.assertTrue(r["blocked"])
            self.assertTrue(r["backup_path"].exists())

    def test_proceeds_when_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            r = preflight_guard(FakeSession(TWO), "http://api", "123456789",
                                dry_run=False, allow_orphan_comments=True, backup_dir=d)
            self.assertFalse(r["blocked"])
            self.assertTrue(r["backup_path"].exists())

    def test_no_comments_no_backup_no_block(self):
        with tempfile.TemporaryDirectory() as d:
            r = preflight_guard(FakeSession("<p>plain</p>"), "http://api", "123456789",
                                dry_run=False, allow_orphan_comments=False, backup_dir=d)
            self.assertEqual(r["count"], 0)
            self.assertIsNone(r["backup_path"])
            self.assertFalse(r["blocked"])


class VerifyAfterUploadTests(unittest.TestCase):
    def test_reports_orphaned_drop(self):
        session = FakeSession('<ac:inline-comment-marker ac:ref="r1">a</ac:inline-comment-marker>')
        after = verify_after_upload(session, "http://api", "123456789", before_count=2)
        self.assertEqual(after, 1)


if __name__ == "__main__":
    unittest.main()
