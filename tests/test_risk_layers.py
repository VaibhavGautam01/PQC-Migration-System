import copy
import json
import tempfile
import unittest
from pathlib import Path

from src import risk_page_data as D
from src import risk_run as RR
from src import risk_score as R


def weights(with_none):
    w = copy.deepcopy(R.load_weights())
    if with_none:
        w["f1_quantum_exposure"]["none"] = 0
    else:
        w["f1_quantum_exposure"].pop("none", None)
    return w


class LayerScoringTests(unittest.TestCase):
    def test_image_has_only_l1_and_three_layers_with_no_protection(self):
        p = RR.score_project("image", weights=weights(False))
        self.assertEqual(p["layers_scored"], ["L1"])
        self.assertEqual(p["no_protection"], ["L2", "L3", "L5"])
        self.assertEqual(p["layers_not_scored_yet"], [])
        self.assertEqual(p["project_score"], 91.9)

    def test_video_l2_is_scored_and_l3_waits_for_the_none_category(self):
        p = RR.score_project("video", weights=weights(False))
        self.assertEqual(p["layers_scored"], ["L1", "L2"])
        self.assertEqual(p["layers_not_scored_yet"], ["L3"])
        self.assertIn("none", p["pending_reason"])
        l2 = p["other_layers"]["L2"]["score"]
        self.assertEqual((l2["overall"], l2["band"]), (35.8, "Moderate"))
        self.assertEqual(p["no_protection"], ["L5"])

    def test_video_l3_scores_about_30_once_none_is_in_the_weights(self):
        p = RR.score_project("video", weights=weights(True))
        self.assertEqual(p["layers_not_scored_yet"], [])
        self.assertIsNone(p["pending_reason"])
        l3 = p["other_layers"]["L3"]["score"]
        self.assertAlmostEqual(l3["overall"], 30.4, delta=0.1)
        self.assertEqual(l3["band"], "Moderate")
        self.assertAlmostEqual(p["project_score"], 64.1, delta=0.1)   # L1 71.8, L2 35.8, L3 30.4

    def test_weakest_link_rule_adding_weaker_layers_never_raises_the_score(self):
        l1_only = RR.score_project("video", weights=weights(False))["L1"]["score"]["overall"]
        two = RR.score_project("video", weights=weights(False))["project_score"]
        three = RR.score_project("video", weights=weights(True))["project_score"]
        self.assertLessEqual(two, l1_only)
        self.assertLessEqual(three, two)

    def test_project_still_ranks_image_above_video(self):
        for with_none in (False, True):
            w = weights(with_none)
            self.assertGreater(RR.score_project("image", weights=w)["project_score"],
                               RR.score_project("video", weights=w)["project_score"])

    def test_z_range_contains_the_central_score_and_follows_z(self):
        p = RR.score_project("video", weights=weights(True))
        self.assertLessEqual(p["z_range"]["min"], p["project_score"])
        self.assertGreaterEqual(p["z_range"]["max"], p["project_score"])
        for e in p["other_layers"].values():
            s = e["z_scenarios"]
            self.assertGreaterEqual(s["5"]["overall"], s["20"]["overall"])

    def test_output_file_carries_the_new_fields(self):
        with tempfile.TemporaryDirectory() as d:
            out = RR.run(out_path=Path(d) / "r.json")
            on_disk = json.loads((Path(d) / "r.json").read_text())
        self.assertEqual(on_disk["projects"]["video"]["no_protection"], ["L5"])
        self.assertIn("other_layers", out["projects"]["image"])


class PageRowsTests(unittest.TestCase):
    def test_layer_rows_list_every_scored_layer(self):
        p = RR.score_project("video", weights=weights(True))
        rows = D.layer_rows(p)
        self.assertEqual([r["Layer"][:2] for r in rows], ["L1", "L2", "L3"])
        self.assertTrue(all(0 <= r["Overall %"] <= 100 for r in rows))

    def test_no_protection_text(self):
        p = RR.score_project("image", weights=weights(False))
        text = D.no_protection_text(p)
        self.assertIn("L2, L3, L5", text)
        self.assertIn("not counted as safe", text)
        self.assertEqual(D.no_protection_text({"no_protection": []}), "")


if __name__ == "__main__":
    unittest.main()
