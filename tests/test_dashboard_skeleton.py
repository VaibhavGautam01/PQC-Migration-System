"""Tests for the final dashboard skeleton (Issue #10).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DASHBOARD = os.path.join(ROOT, "docs", "final_dashboard.md")
EXPECTED = ["Summary", "Detection", "Mapping", "Risk", "Demo", "Conclusion"]


class TestDashboardSkeleton(unittest.TestCase):
    def setUp(self):
        with open(DASHBOARD, encoding="utf-8") as fh:
            self.text = fh.read()

    def test_has_a_title(self):
        self.assertTrue(self.text.startswith("# Final Dashboard"))

    def test_has_the_six_sections_in_order(self):
        headers = re.findall(r"^## (.+)$", self.text, flags=re.MULTILINE)
        self.assertEqual(headers, EXPECTED)

    def test_every_section_has_content(self):
        parts = re.split(r"^## .+$", self.text, flags=re.MULTILINE)[1:]
        self.assertEqual(len(parts), 6)
        for name, body in zip(EXPECTED, parts):
            with self.subTest(section=name):
                self.assertTrue(body.strip())


if __name__ == "__main__":
    unittest.main()
