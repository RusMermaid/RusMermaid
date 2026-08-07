import json
import unittest
from pathlib import Path

from scripts import update_recent_visitors as visitors


ROOT = Path(__file__).resolve().parents[1]


class RecentVisitorsTests(unittest.TestCase):
    def test_add(self):
        current = ["fiorin", "UltWolf", "charlie-sans", "martimine26", "Quofite"]
        self.assertEqual(
            visitors.add(current, "octocat", "RusMermaid"),
            ["octocat", "fiorin", "UltWolf", "charlie-sans", "martimine26"],
        )

    def test_repeat(self):
        current = ["fiorin", "UltWolf", "charlie-sans", "martimine26", "Quofite"]
        self.assertEqual(
            visitors.add(current, "ultwolf", "RusMermaid"),
            ["ultwolf", "fiorin", "charlie-sans", "martimine26", "Quofite"],
        )

    def test_owner(self):
        current = ["RusMermaid", "fiorin", "UltWolf"]
        self.assertEqual(
            visitors.add(current, "rusmermaid", "RusMermaid"),
            ["fiorin", "UltWolf"],
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            visitors.valid("not/a-login")

    def test_cells(self):
        rendered = visitors.cells(
            ["fiorin", "UltWolf", "charlie-sans", "martimine26", "Quofite"]
        )
        self.assertEqual(rendered.count('<td align="center" valign="top" width="14%">'), 5)
        self.assertEqual(rendered.count('width="52" height="52"'), 5)
        self.assertIn("@charlie&#8209;sans", rendered)

    def test_sync(self):
        data = json.loads(
            (ROOT / "data/recent_visitors.json").read_text(encoding="utf-8")
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        start = readme.index(visitors.BEGIN_MARKER) + len(visitors.BEGIN_MARKER)
        end = readme.index(visitors.END_MARKER)
        self.assertEqual(
            readme[start:end].strip(), visitors.cells(data).strip()
        )
        self.assertNotIn("RusMermaid", data)


if __name__ == "__main__":
    unittest.main()
