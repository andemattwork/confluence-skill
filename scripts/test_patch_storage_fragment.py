import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_storage_fragment


class PatchStorageFragmentTests(unittest.TestCase):
    def test_exact_replacement_requires_single_match(self):
        body = "<p>before</p><ac:structured-macro ac:name=\"note\" /><p>after</p>"
        updated, count = patch_storage_fragment.apply_replacement(
            body,
            '<ac:structured-macro ac:name="note" />',
            '<ac:structured-macro ac:name="info" />',
            None,
        )

        self.assertEqual(count, 1)
        self.assertIn('ac:name="info"', updated)
        self.assertNotIn('ac:name="note"', updated)

    def test_exact_replacement_rejects_multiple_matches(self):
        body = "target target"

        with self.assertRaisesRegex(SystemExit, "Expected exact old fragment once, found 2"):
            patch_storage_fragment.apply_replacement(body, "target", "replacement", None)

    def test_regex_replacement_requires_single_match(self):
        body = "<h2>Design</h2><ac:structured-macro ac:name=\"plantuml\">old</ac:structured-macro>"

        updated, count = patch_storage_fragment.apply_replacement(
            body,
            None,
            '<ac:structured-macro ac:name="drawio" />',
            r'<ac:structured-macro\s+ac:name="plantuml"[\s\S]*?</ac:structured-macro>',
        )

        self.assertEqual(count, 1)
        self.assertIn('ac:name="drawio"', updated)

    def test_validate_fragments_rejects_missing_required_and_present_forbidden(self):
        with self.assertRaisesRegex(SystemExit, r"missing_required=\['required'\].*present_forbidden=\['forbidden'\]"):
            patch_storage_fragment.validate_fragments("forbidden", ["required"], ["forbidden"])


if __name__ == "__main__":
    unittest.main()
