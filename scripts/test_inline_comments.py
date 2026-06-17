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


if __name__ == "__main__":
    unittest.main()
