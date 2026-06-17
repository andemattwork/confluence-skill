import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inline_comments import extract_inline_markers, count_inline_markers


class MarkerExtractionTests(unittest.TestCase):
    def test_empty_and_none(self):
        self.assertEqual(extract_inline_markers(""), [])
        self.assertEqual(count_inline_markers(""), 0)

    def test_no_markers(self):
        self.assertEqual(count_inline_markers("<p>plain body</p>"), 0)

    def test_single_marker(self):
        xml = '<p>a<ac:inline-comment-marker ac:ref="r1">word</ac:inline-comment-marker>b</p>'
        markers = extract_inline_markers(xml)
        self.assertEqual(markers, [{"ref": "r1", "anchored_text": "word"}])
        self.assertEqual(count_inline_markers(xml), 1)

    def test_one_comment_split_across_fragments(self):
        # A single comment's marker repeats with the SAME ref across element
        # boundaries; fragments must join in document order and count as ONE.
        xml = (
            '<strong>He<ac:inline-comment-marker ac:ref="r1">llo</ac:inline-comment-marker></strong>'
            '<span><ac:inline-comment-marker ac:ref="r1"> </ac:inline-comment-marker></span>'
            '<ac:inline-comment-marker ac:ref="r1">wor</ac:inline-comment-marker>ld'
        )
        markers = extract_inline_markers(xml)
        self.assertEqual(markers, [{"ref": "r1", "anchored_text": "llo wor"}])
        self.assertEqual(count_inline_markers(xml), 1)

    def test_two_distinct_refs(self):
        xml = (
            '<ac:inline-comment-marker ac:ref="r1">one</ac:inline-comment-marker>'
            '<ac:inline-comment-marker ac:ref="r2">two</ac:inline-comment-marker>'
        )
        self.assertEqual(count_inline_markers(xml), 2)

    def test_ref_not_first_attribute(self):
        xml = '<ac:inline-comment-marker data-x="y" ac:ref="r1">t</ac:inline-comment-marker>'
        self.assertEqual(count_inline_markers(xml), 1)

    def test_nested_tags_stripped(self):
        xml = '<ac:inline-comment-marker ac:ref="r1"><strong>bo</strong>ld</ac:inline-comment-marker>'
        self.assertEqual(extract_inline_markers(xml)[0]["anchored_text"], "bold")


import json
import tempfile

from inline_comments import (
    fetch_inline_comments, correlate, write_backup, backup_from_page,
)


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
    """Routes GETs by URL: page content vs child/comment."""
    def __init__(self, page=None, comments_status=200, comments_payload=None,
                 comment_error=False):
        self._page = page
        self._comments_status = comments_status
        self._comments_payload = comments_payload or {"results": []}
        self._comment_error = comment_error

    def get(self, url, params=None):
        if url.endswith("/child/comment"):
            if self._comment_error:
                raise RuntimeError("network down")
            return FakeResp(self._comments_status, self._comments_payload)
        return FakeResp(200, self._page)


class FetchInlineCommentsTests(unittest.TestCase):
    def test_non_200_returns_empty(self):
        session = FakeSession(comments_status=404)
        self.assertEqual(fetch_inline_comments(session, "http://api", "1"), [])

    def test_exception_returns_empty(self):
        session = FakeSession(comment_error=True)
        self.assertEqual(fetch_inline_comments(session, "http://api", "1"), [])

    def test_json_returns_none_is_safe(self):
        class NoneJsonSession:
            def get(self, url, params=None):
                class R:
                    status_code = 200
                    def json(self_inner):
                        return None
                return R()
        self.assertEqual(fetch_inline_comments(NoneJsonSession(), "http://api", "1"), [])

    def test_parses_fields_verbatim(self):
        payload = {"results": [{
            "id": "c1",
            "body": {"storage": {"value": "<p>nice catch</p>"}},
            "version": {"by": {"displayName": "Reviewer"}, "when": "2026-01-01"},
            "extensions": {
                "inlineProperties": {"markerRef": "r1", "originalSelection": "word"},
                "resolution": {"status": "closed"},
            },
        }]}
        session = FakeSession(comments_payload=payload)
        out = fetch_inline_comments(session, "http://api", "1")
        self.assertEqual(out[0]["marker_ref"], "r1")
        self.assertEqual(out[0]["body_text"], "nice catch")
        self.assertEqual(out[0]["author"], "Reviewer")
        self.assertEqual(out[0]["status"], "closed")


class CorrelateTests(unittest.TestCase):
    def test_join_and_keep_unmatched(self):
        markers = [{"ref": "r1", "anchored_text": "word"}]
        comments = [
            {"marker_ref": "r1", "body_text": "b1", "author": "A", "created": "",
             "status": "open", "original_selection": "word"},
            {"marker_ref": "rX", "body_text": "orphan", "author": "B", "created": "",
             "status": "closed", "original_selection": ""},
        ]
        result = correlate(markers, comments)
        self.assertEqual(result[0]["ref"], "r1")
        self.assertEqual(result[0]["body_text"], "b1")
        # unmatched API comment is preserved, not dropped
        self.assertTrue(any(c["body_text"] == "orphan" for c in result))


class WriteBackupTests(unittest.TestCase):
    def test_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as d:
            meta = {"id": "123456789", "version": 2, "title": "Example",
                    "url": "/x", "exported_at": "2026-06-16T00:00:00"}
            correlated = [{"ref": "r1", "anchored_text": "word", "body_text": "b1",
                           "author": "A", "created": "", "status": "open",
                           "original_selection": "word"}]
            path = write_backup(meta, correlated, d)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["comment_count"], 1)
            self.assertEqual(data["comments"][0]["anchored_text"], "word")
            self.assertEqual(data["page"]["id"], "123456789")


class BackupFromPageTests(unittest.TestCase):
    def test_end_to_end_with_fakes(self):
        page = {
            "id": "123456789", "title": "Example",
            "version": {"number": 2}, "_links": {"webui": "/pages/123456789"},
            "body": {"storage": {"value":
                '<ac:inline-comment-marker ac:ref="r1">word</ac:inline-comment-marker>'}},
        }
        payload = {"results": [{
            "id": "c1", "body": {"storage": {"value": "b1"}},
            "version": {"by": {"displayName": "A"}, "when": ""},
            "extensions": {"inlineProperties": {"markerRef": "r1",
                           "originalSelection": "word"},
                           "resolution": {"status": "open"}},
        }]}
        session = FakeSession(page=page, comments_payload=payload)
        with tempfile.TemporaryDirectory() as d:
            path = backup_from_page(session, "http://api", page, d)
            data = json.loads(path.read_text())
            self.assertEqual(data["comment_count"], 1)
            self.assertEqual(data["comments"][0]["body_text"], "b1")
            self.assertEqual(data["page"]["version"], 2)


if __name__ == "__main__":
    unittest.main()
