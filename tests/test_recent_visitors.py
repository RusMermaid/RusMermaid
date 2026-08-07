import json
import unittest
from pathlib import Path

from scripts import update_recent_visitors as visitors


ROOT = Path(__file__).resolve().parents[1]


class RecentVisitorsTests(unittest.TestCase):
    def test_new_check_in_is_first_and_list_stays_at_three(self):
        current = ["fiorin", "UltWolf", "charlie-sans"]
        self.assertEqual(
            visitors.update_visitors(current, "octocat", "RusMermaid"),
            ["octocat", "fiorin", "UltWolf"],
        )

    def test_repeat_check_in_moves_to_front_without_duplicates(self):
        current = ["fiorin", "UltWolf", "charlie-sans"]
        self.assertEqual(
            visitors.update_visitors(current, "ultwolf", "RusMermaid"),
            ["ultwolf", "fiorin", "charlie-sans"],
        )

    def test_owner_is_never_included(self):
        current = ["RusMermaid", "fiorin", "UltWolf"]
        self.assertEqual(
            visitors.update_visitors(current, "rusmermaid", "RusMermaid"),
            ["fiorin", "UltWolf"],
        )

    def test_invalid_login_is_rejected(self):
        with self.assertRaises(ValueError):
            visitors.validate_login("not/a-login")

    def test_repository_data_and_readme_are_synchronized(self):
        data = json.loads(
            (ROOT / "data/recent_visitors.json").read_text(encoding="utf-8")
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        start = readme.index(visitors.BEGIN_MARKER) + len(visitors.BEGIN_MARKER)
        end = readme.index(visitors.END_MARKER)
        self.assertEqual(
            readme[start:end].strip(), visitors.render_cells(data).strip()
        )
        self.assertNotIn("RusMermaid", data)


if __name__ == "__main__":
    unittest.main()
