import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import risk_report_sections as rrs


class TestSections(unittest.TestCase):
    def test_unscored_numbers_are_labelled_not_invented(self):
        text = rrs.section_risk_percentages({}) + rrs.section_before_after({})
        self.assertIn(rrs.NOT_SCORED, text)
        self.assertNotRegex(text.split("Project score")[0].split("|---|---|---|---|---|---|")[1], r"\d+\.\d")

    def test_scores_are_shown_when_provided(self):
        scores = {"image": {"layers": {"L1": {"quantum": 1.0, "classical": 2.0, "overall": 3.0,
                                              "band": "Low", "after_overall": 0.5}}, "project_score": 3.0}}
        self.assertIn("| L1 | RSA (textbook, no padding) | 1.0 | 2.0 | 3.0 | Low |", rrs.section_risk_percentages(scores))
        self.assertIn("0.5", rrs.section_before_after(scores))

    def test_read_scores_reads_real_file(self):
        scores = rrs.read_scores()
        self.assertIn("L1", scores["image"]["layers"])
        self.assertEqual(scores["image"]["layers"]["L1"]["overall"], 91.9)
        self.assertEqual(scores["image"]["layers"]["L1"]["after_overall"], 4.7)
        self.assertIn("L2", scores["video"]["layers"])
        self.assertIsNone(scores["video"]["layers"]["L1"]["after_overall"])

    def test_read_scores_missing_file_gives_empty(self):
        self.assertEqual(rrs.read_scores(scores_path="no_such_file.json"), {})

    def test_advisor_section_mentions_ml_kem_768(self):
        self.assertIn("ML-KEM-768", rrs.section_advisor())

    def test_reference_cases_present_and_ordered(self):
        overall = [float(c[3]) for c in rrs.REFERENCE_CASES]
        self.assertEqual(overall, sorted(overall, reverse=True))
        self.assertIn("84.1", rrs.section_reference_cases())


if __name__ == "__main__":
    unittest.main()