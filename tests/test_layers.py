import unittest
from src import layers


class LayerMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = layers.load_findings()
        cls.m = layers.build_layer_map(cls.findings)

    def test_every_finding_is_assigned(self):
        self.assertEqual(self.m["unmapped"], [])

    def test_counts_add_up(self):
        total = sum(len(v) for p in ("image", "video") for v in self.m[p].values())
        self.assertEqual(total, len(self.findings))

    def test_rsa_is_l1_in_both_projects(self):
        for p in ("image", "video"):
            self.assertTrue(all(f["primitive"] == "RSA" for f in self.m[p]["L1"]))

    def test_video_frame_selector_is_l2(self):
        l2 = self.m["video"]["L2"]
        self.assertEqual(len(l2), 1)
        self.assertIn("frame_selector", l2[0]["file"])

    def test_image_has_no_scanned_l2(self):
        self.assertEqual(len(self.m["image"]["L2"]), 0)

    def test_unknown_project_is_unmapped(self):
        self.assertIsNone(layers.assign_layer({"project": "x", "primitive": "RSA", "file": "a.py"}))

    def test_manual_layers_declared(self):
        self.assertEqual(layers.LAYER_DEFS["video"]["L3"]["source"], "manual")

    def test_l3_crc32_evidence(self):
        ev = layers.LAYER_DEFS["video"]["L3"]["evidence"]
        self.assertEqual(ev["lines"], [137, 180])


if __name__ == "__main__":
    unittest.main()
