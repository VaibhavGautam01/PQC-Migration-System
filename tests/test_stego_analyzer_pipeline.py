import hashlib
import tempfile
import unittest
from pathlib import Path

from src import risk_score as rs
from stego_analyzer import NotImplementedStage, pipeline as sa, schema


def fake_stages(method="lsb", cipher=None, blob=b"\x01" * 16, ext_ok=True, **extra):
    """Stages that return fixed answers, so the flow can be tested without the real stages."""
    calls = []

    def detect(path):
        calls.append("detect")
        return {"method": method, "confidence": 0.9, "test_set_error_rate": 0.05, "features": {}}

    def extract(path, m):
        calls.append("extract")
        return {"ok": ext_ok, "blob": blob if ext_ok else b"", "source": "fake"}

    def identify(b, public_key=None):
        calls.append("identify")
        return cipher

    def attack_toy(key, b):
        calls.append("attack_toy")
        return {"state": "broken_toy", "run_id": f"q2-shor-N{key['n']}", "label": schema.QUANTUM_LABEL,
                "recovered_message": "PQC!"}

    def attack_classical(key, b):
        calls.append("attack_classical")
        return {"state": "broken_classical_small_key", "tool": "fake", "recovered_message": "PQC!"}

    def estimate(bits):
        calls.append("estimate")
        return {"logical_qubits_2n_plus_3": 2 * bits + 3, "published": "Gidney and Ekera 2021, ESTIMATE, not measured"}

    stages = {"detect": detect, "extract": extract, "identify": identify, "attack_toy": attack_toy,
              "attack_classical": attack_classical, "estimate": estimate}
    stages.update(extra)
    return stages, calls


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.img = Path(self.tmp.name) / "stego.png"
        self.img.write_bytes(b"pretend image bytes")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, public_key=None, **kw):
        stages, calls = fake_stages(**kw)
        report = sa.analyze(self.img, stages, public_key=public_key)
        return report, calls

    # ---- routing
    def test_route_table(self):
        route = sa.choose_route
        self.assertEqual(route({"kind": "textbook_rsa", "n": 15, "modulus_bits": 4}), "shor_toy")
        self.assertEqual(route({"kind": "textbook_rsa", "n": 35, "modulus_bits": 6}), "shor_toy")
        self.assertEqual(route({"kind": "textbook_rsa", "n": 221, "modulus_bits": 8}), "classical_small_key")
        self.assertEqual(route({"kind": "textbook_rsa", "n": None, "modulus_bits": 64}), "classical_small_key")
        self.assertEqual(route({"kind": "textbook_rsa", "modulus_bits": 256}), "estimate")
        self.assertEqual(route({"kind": "textbook_rsa", "n": None, "modulus_bits": None}), "needs_public_key")
        self.assertEqual(route({"kind": "oaep_style", "modulus_bits": 2048}), "estimate")
        self.assertEqual(route({"kind": "ml_kem_aes_gcm"}), "resists")
        self.assertEqual(route({"kind": "unrecognised"}), "unrecognised")
        self.assertEqual(route(None), "unrecognised")

    # ---- the score is the engine's score
    def test_score_equals_the_engine_for_the_same_configuration(self):
        want = rs.score_layer("shor_broken", "no_padding_deterministic", "keyless", modulus_bits=256)
        got = sa.score_for({"kind": "textbook_rsa", "modulus_bits": 256})
        self.assertEqual(got["overall"], round(want["overall"], 1))
        self.assertEqual(got["overall"], 91.9)                       # same as the image before/after table

    def test_worked_reference_values_from_the_plan(self):
        self.assertEqual(sa.score_for({"kind": "oaep_style", "modulus_bits": 2048})["overall"], 50.8)
        self.assertEqual(sa.score_for({"kind": "ml_kem_aes_gcm"})["overall"], 4.7)

    def test_unrecognised_cipher_gets_no_score(self):
        self.assertIsNone(sa.score_for({"kind": "unrecognised"}))

    def test_exposure_follows_the_hiding_method(self):
        self.assertEqual(sa.exposure_for("lsb"), "keyless")
        self.assertEqual(sa.exposure_for("xor_lsb"), "bypassable")

    # ---- full flows
    def test_toy_rsa_is_broken_by_the_shor_stage_and_reported_with_its_label(self):
        r, calls = self.run_with(public_key={"n": 15, "e": 7}, cipher={"kind": "textbook_rsa", "n": 15, "modulus_bits": 4})
        self.assertEqual(r["attack"]["state"], "broken_toy")
        self.assertEqual(r["attack"]["label"], "Aer simulator, toy size")
        self.assertEqual(r["attack"]["recovered_message"], "PQC!")
        self.assertEqual(r["technique"]["algorithm"], "shor")
        self.assertEqual((r["pipeline_status"], r["problems"]), ("complete", []))
        self.assertIn("attack_toy", calls)
        self.assertIsNotNone(r["score"])

    def test_the_stage_gets_the_n_read_from_the_image_and_changes_with_it(self):
        seen = []

        def spy(key, blob):
            seen.append(key["n"])
            return {"state": "broken_toy", "run_id": f"r{key['n']}", "label": schema.QUANTUM_LABEL,
                    "recovered_message": "x"}

        for n, bits in ((15, 4), (21, 5), (35, 6)):
            self.run_with(public_key={"n": n, "e": 3}, cipher={"kind": "textbook_rsa", "n": n, "modulus_bits": bits},
                          attack_toy=spy)
        self.assertEqual(seen, [15, 21, 35])                         # rule 6: a different N reaches the stage

    def test_mid_size_key_uses_the_classical_small_key_attack(self):
        r, calls = self.run_with(public_key={"n": 2 ** 63 + 1, "e": 3},
                                 cipher={"kind": "textbook_rsa", "n": None, "modulus_bits": 64})
        self.assertEqual(r["attack"]["state"], "broken_classical_small_key")
        self.assertNotIn("attack_toy", calls)
        self.assertEqual(r["problems"], [])

    def test_large_key_gets_a_labelled_estimate_and_never_a_time(self):
        r, calls = self.run_with(public_key={"n": 2 ** 1023 + 1, "e": 3},
                                 cipher={"kind": "textbook_rsa", "n": None, "modulus_bits": 1024})
        self.assertEqual(r["attack"]["state"], "vulnerable_estimate")
        self.assertIn("ESTIMATE", r["estimate"]["published"])
        self.assertEqual(r["problems"], [])
        self.assertNotIn("attack_toy", calls)

    def test_ml_kem_payload_resists_and_no_attack_stage_runs(self):
        r, calls = self.run_with(cipher={"kind": "ml_kem_aes_gcm"})
        self.assertEqual(r["attack"]["state"], "resists")
        self.assertEqual(r["technique"]["algorithm"], "grover")
        self.assertEqual(r["score"]["overall"], 4.7)
        self.assertEqual(calls, ["detect", "extract", "identify"])

    def test_clean_image_is_unrecognised_and_extraction_is_not_tried(self):
        r, calls = self.run_with(method="clean_or_unknown", cipher={"kind": "textbook_rsa"})
        self.assertEqual(r["attack"]["state"], "unrecognised")
        self.assertIsNone(r["score"])
        self.assertEqual(calls, ["detect"])

    def test_failed_extraction_is_unrecognised(self):
        r, calls = self.run_with(ext_ok=False, cipher={"kind": "textbook_rsa"})
        self.assertEqual(r["attack"]["state"], "unrecognised")
        self.assertNotIn("identify", calls)

    def test_unknown_cipher_is_unrecognised_with_no_score_and_no_guess(self):
        r, calls = self.run_with(cipher={"kind": "unrecognised"})
        self.assertEqual(r["attack"]["state"], "unrecognised")
        self.assertIsNone(r["score"])
        self.assertEqual(r["problems"], [])

    # ---- stages that are not built, or that fail
    def test_without_the_pinned_project_the_pipeline_stops_and_says_what_to_do(self):
        from unittest import mock
        from stego_analyzer import extract
        with mock.patch.object(extract, "PINNED_DIR", Path(self.tmp.name) / "no_such_project"):
            r = sa.analyze(self.img)
        self.assertIn("stopped at detect_method", r["pipeline_status"])
        self.assertIn("git submodule update --init", r["pipeline_status"])
        self.assertIsNone(r["attack"])
        self.assertIsNone(r["score"])
        self.assertEqual(r["problems"], [])

    def test_the_stage_that_is_still_a_stub_is_named(self):
        from stego_analyzer import attack_classical
        with self.assertRaises(NotImplementedStage):
            attack_classical.attack({"n": 2 ** 63 + 1, "e": 3}, b"00")

    def test_a_stage_that_is_missing_later_stops_there_and_keeps_earlier_results(self):
        def not_built(b, public_key=None):
            raise NotImplementedStage("cipher_identify")

        r, _ = self.run_with(identify=not_built)
        self.assertEqual(r["pipeline_status"], "stopped at cipher_identify: not implemented yet")
        self.assertEqual(r["hiding"]["method"], "lsb")
        self.assertIsNone(r["attack"])

    def test_a_stage_error_is_shown_not_hidden(self):
        def broken(path):
            raise ValueError("bad pixels")

        r, _ = self.run_with(detect=broken)
        self.assertIn("ValueError: bad pixels", r["pipeline_status"])

    def test_rsa_without_a_public_key_is_not_attacked_and_says_why(self):
        r, calls = self.run_with(cipher={"kind": "textbook_rsa", "n": None, "modulus_bits": None})
        self.assertEqual(r["attack"]["state"], "unrecognised")
        self.assertIn("public key", r["attack"]["reason"])
        self.assertIsNone(r["score"])
        self.assertNotIn("attack_toy", calls)
        self.assertEqual(r["problems"], [])

    def test_public_key_fills_in_the_modulus_the_identifier_did_not_return(self):
        r, _ = self.run_with(public_key={"n": 2 ** 255 + 95, "e": 65537},
                             cipher={"kind": "textbook_rsa", "n": None, "modulus_bits": None})
        self.assertEqual(r["cipher"]["modulus_bits"], 256)
        self.assertEqual(r["attack"]["state"], "vulnerable_estimate")
        self.assertEqual(r["score"]["overall"], 91.9)

    def test_public_key_is_recorded_and_checked(self):
        r, _ = self.run_with(public_key={"n": 15, "e": 7}, cipher={"kind": "ml_kem_aes_gcm"})
        self.assertEqual(r["input"]["public_key"], {"n": 15, "e": 7})
        with self.assertRaises(ValueError):
            self.run_with(public_key={"n": 2, "e": 7}, cipher={"kind": "ml_kem_aes_gcm"})

    def test_evidence_rows_point_at_the_records(self):
        r, _ = self.run_with(public_key={"n": 15, "e": 7}, cipher={"kind": "textbook_rsa", "n": 15, "modulus_bits": 4},
                             attack_toy=lambda k, b: {"state": "broken_toy", "run_id": "q2-x", "label": schema.QUANTUM_LABEL,
                                                      "recovered_message": "x",
                                                      "evidence": {"record_file": "data/quantum_runs.json", "run_id": "q2-x"},
                                                      "runs_tried": [{"run_id": "q2-x"}]})
        rows = sa.evidence_rows(r)
        self.assertEqual(rows[0]["where"], "data/quantum_runs.json")
        self.assertTrue(any(x["what"] == "score" for x in rows))

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            sa.analyze(Path(self.tmp.name) / "nope.png")

    def test_input_is_recorded_with_its_hash(self):
        r, _ = self.run_with(cipher={"kind": "ml_kem_aes_gcm"})
        self.assertEqual(r["input"]["sha256"], hashlib.sha256(b"pretend image bytes").hexdigest())
        self.assertEqual(r["input"]["bytes"], len(b"pretend image bytes"))

    def test_summary_text_has_no_result_line_for_an_unfinished_run(self):
        from unittest import mock
        from stego_analyzer import extract
        # the pinned project must be absent so the run stops early, whatever machine this runs on
        with mock.patch.object(extract, "PINNED_DIR", Path(self.tmp.name) / "no_such_project"):
            text = sa.summary_text(sa.analyze(self.img))
        self.assertNotIn("Result:", text)
        self.assertIn("stopped at detect_method", text)


class SchemaRuleTests(unittest.TestCase):
    def base(self, **attack):
        return {"schema_version": 1, "created_utc": "x", "input": {}, "pipeline_status": "complete",
                "limits": ["l"], "attack": attack, "score": {"overall": 1}}

    def test_recovered_message_only_for_a_broken_state(self):
        r = self.base(state="vulnerable_estimate", recovered_message="x")
        r["estimate"] = {"published": "ESTIMATE"}
        self.assertTrue(any("recovered_message" in p for p in schema.validate_report(r)))

    def test_broken_toy_needs_the_label_and_a_run_id(self):
        r = self.base(state="broken_toy", recovered_message="x")
        text = " ".join(schema.validate_report(r))
        self.assertIn("label", text)
        self.assertIn("run_id", text)

    def test_estimate_must_not_carry_a_time(self):
        r = self.base(state="vulnerable_estimate")
        r["estimate"] = {"published": "ESTIMATE", "seconds_to_break": 5}
        self.assertTrue(any("must not carry a time" in p for p in schema.validate_report(r)))

    def test_estimate_must_be_labelled_estimate(self):
        r = self.base(state="vulnerable_estimate")
        r["estimate"] = {"logical_qubits_2n_plus_3": 4099, "published": "Gidney and Ekera 2021"}
        self.assertTrue(any("must say ESTIMATE" in p for p in schema.validate_report(r)))

    def test_unrecognised_must_not_have_a_score(self):
        r = self.base(state="unrecognised")
        self.assertTrue(any("must not get a score" in p for p in schema.validate_report(r)))

    def test_incomplete_pipeline_must_not_claim_a_state(self):
        r = self.base(state="resists")
        r["pipeline_status"] = "stopped at extract: not implemented yet"
        self.assertTrue(any("incomplete pipeline" in p for p in schema.validate_report(r)))

    def test_a_good_resists_report_has_no_problems(self):
        r = self.base(state="resists")
        self.assertEqual(schema.validate_report(r), [])


if __name__ == "__main__":
    unittest.main()
