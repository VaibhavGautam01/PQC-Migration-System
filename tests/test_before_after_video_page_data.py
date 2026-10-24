import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import before_after_page_data as ba  # type: ignore # noqa: E402


class TestVideoPageData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = ba.load_video()
        cls.row = ba.row_for(cls.data, 2048)

    def test_file_loads_and_has_the_three_sizes(self):
        self.assertEqual(ba.size_options(self.data), [1024, 2048, 3072])
        self.assertEqual(self.data["project"], "video")

    def test_summary_has_bands_from_the_same_engine(self):
        s = ba.video_summary(self.row)
        self.assertEqual((round(s["before"], 1), round(s["after"], 1)), (64.1, 29.8))
        self.assertEqual((s["before_band"], s["after_band"]), ("High", "Moderate"))
        self.assertGreater(s["drop"], 0)

    def test_layer_rows_cover_l1_to_l3_and_l2_is_not_credited(self):
        rows = ba.video_layer_rows(self.row)
        self.assertEqual([r["layer"][:2] for r in rows], ["L1", "L2", "L3"])
        l2 = rows[1]
        self.assertIsNone(l2["after"])
        self.assertEqual(l2["after_band"], "not credited")
        for r in (rows[0], rows[2]):
            self.assertLess(r["after"], r["before"])

    def test_chart_rows_leave_out_the_uncredited_after_bar(self):
        rows = ba.video_chart_rows(self.row)
        self.assertEqual(len(rows), 5)                      # three before bars, two after bars
        self.assertFalse(any(r["layer"] == "L2" and r["setup"] == "after" for r in rows))

    def test_scenarios_sorted_and_after_below_before(self):
        rows = ba.video_scenario_rows(self.row)
        self.assertEqual([r["z"] for r in rows], [5, 10, 20])
        for r in rows:
            self.assertLess(r["after"], r["before"])

    def test_sensitivity_rows_say_after_is_below_before_every_time(self):
        rows = ba.video_sensitivity_rows(self.row)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["after_below_before"] == 1.0 for r in rows))

    def test_missing_file_gives_none_not_a_crash(self):
        self.assertIsNone(ba.load_video("no_such_file.json"))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            self.assertIsNone(ba.load_video(p))

    def test_not_credited_note_and_exposure_note_are_in_the_file(self):
        self.assertIn("L2", self.data["not_credited"])
        self.assertIn("bypassable", self.data["exposure_note"])


if __name__ == "__main__":
    unittest.main()
