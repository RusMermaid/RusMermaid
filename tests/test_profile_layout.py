import os
import tempfile
import unittest
from pathlib import Path

import main as chess_main
from scripts import generate_wakatime_card as wakatime
from src import markdown


class ProfileLayoutTests(unittest.TestCase):
    def test_moves(self):
        rendered = markdown.generate_last_moves()
        lines = [line for line in rendered.splitlines() if line.startswith("|")]

        self.assertEqual(
            lines[0],
            "| Turn | Move | Author | Turn | Move | Author |",
        )
        self.assertEqual(
            lines[1],
            "| :--: | :--: | :--: | :--: | :--: | :--: |",
        )
        self.assertEqual(len(lines[2:]), 3)
        self.assertEqual(rendered.count('<img src="img/'), 6)
        self.assertNotIn("[ @", rendered)

    def test_visit(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data/recent_visitors.json").write_text(
                '["older"]\n',
                encoding="utf-8",
            )
            readme = (
                "before\n<!-- BEGIN RECENT VISITORS -->\n"
                "old cells\n<!-- END RECENT VISITORS -->\nafter\n"
            )
            try:
                os.chdir(root)
                updated = chess_main.visit(
                    readme,
                    "@new-player",
                    "@RusMermaid",
                )
            finally:
                os.chdir(original_cwd)

            self.assertIn("@new&#8209;player", updated)
            self.assertIn("@older", updated)
            self.assertNotIn("old cells", updated)

    def test_wakatime(self):
        rendered = wakatime.render_svg(
            [{
                "name": "C#",
                "total_seconds": 3780 * 3600,
                "color": "#5a4028",
                "estimated": True,
            }]
        )
        self.assertIn("lifetime + live worker time", rendered)
        self.assertNotIn("initial lifetime estimate + live WakaTime updates", rendered)
        self.assertEqual(wakatime.OUTPUT_PATH, Path("assets/LAllTimeCoding.svg"))


if __name__ == "__main__":
    unittest.main()
