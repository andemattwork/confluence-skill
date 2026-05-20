import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import replace_macro_with_drawio


class ReplaceMacroWithDrawioTests(unittest.TestCase):
    def test_drawio_macro_contains_editable_diagram_parameters(self):
        macro = replace_macro_with_drawio.drawio_macro("Architecture", 800, 400, 2)

        self.assertIn('ac:name="drawio"', macro)
        self.assertIn('<ac:parameter ac:name="diagramName">Architecture</ac:parameter>', macro)
        self.assertIn('<ac:parameter ac:name="diagramWidth">800</ac:parameter>', macro)
        self.assertIn('<ac:parameter ac:name="height">400</ac:parameter>', macro)
        self.assertIn('<ac:parameter ac:name="revision">2</ac:parameter>', macro)

    def test_replace_macro_after_heading_replaces_one_target_macro(self):
        body = (
            '<h2>Design</h2>'
            '<ac:structured-macro ac:name="plantuml"><ac:plain-text-body><![CDATA[@startuml\n@enduml]]></ac:plain-text-body></ac:structured-macro>'
            '<h2>Other</h2>'
            '<ac:structured-macro ac:name="plantuml">keep</ac:structured-macro>'
        )
        replacement = '<ac:structured-macro ac:name="drawio" />'

        updated = replace_macro_with_drawio.replace_macro_after_heading(
            body,
            '<h2>Design</h2>',
            'plantuml',
            replacement,
        )

        self.assertIn(replacement, updated)
        self.assertIn('<h2>Other</h2><ac:structured-macro ac:name="plantuml">keep</ac:structured-macro>', updated)

    def test_replace_macro_after_heading_rejects_ambiguous_match(self):
        body = '<h2>Design</h2><p>No macro here</p>'

        with self.assertRaisesRegex(SystemExit, "Expected one plantuml macro after heading, found 0"):
            replace_macro_with_drawio.replace_macro_after_heading(
                body,
                '<h2>Design</h2>',
                'plantuml',
                '<ac:structured-macro ac:name="drawio" />',
            )

    def test_validate_requires_drawio_macro_and_diagram_name(self):
        with self.assertRaisesRegex(SystemExit, "Draw.io validation failed"):
            replace_macro_with_drawio.validate("<p>No macro</p>", "Architecture", [], [])


if __name__ == "__main__":
    unittest.main()
