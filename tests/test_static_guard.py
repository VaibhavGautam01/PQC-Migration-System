import unittest

from src import quantum_guard as G

CLEAN = '''
import math
def build_unitary(a, q, N):
    mult = pow(a, 2 ** q, N)        # the oracle the algorithm is given: allowed
    return mult
'''


class GuardCatchesShortcuts(unittest.TestCase):
    def test_clean_builder_passes(self):
        self.assertEqual(G.scan_source(CLEAN, "all"), [])

    def test_sympy_import_is_flagged(self):
        self.assertTrue(G.scan_source("from sympy.ntheory import n_order\n", "all"))
        self.assertTrue(G.scan_source("import sympy\n", "all"))

    def test_forbidden_helper_import_is_flagged(self):
        self.assertTrue(G.scan_source("from mylib import factorint\n", "all"))

    def test_forbidden_call_is_flagged(self):
        src = "def build_x(a, N):\n    r = n_order(a, N)\n    return r\n"
        self.assertTrue(G.scan_source(src, "all"))
        src2 = "def build_x(a, N):\n    return sympy.ntheory.factorint(N)\n"
        self.assertTrue(G.scan_source(src2, "all"))

    def test_period_search_loop_is_flagged(self):
        src = ("def build_x(a, N):\n"
               "    for r in range(1, N):\n"
               "        if pow(a, r, N) == 1:\n"
               "            return r\n")
        self.assertTrue(G.scan_source(src, "all"))
        src_while = ("def build_x(a, N):\n    r = 1\n"
                     "    while pow(a, r, N) != 1:\n        r += 1\n    return r\n")
        self.assertTrue(G.scan_source(src_while, "all"))

    def test_bounded_check_of_a_measured_candidate_is_allowed(self):
        src = ("def post(y, a, N, r0):\n"
               "    for k in (1, 2, 3, 4):\n"
               "        if pow(a, r0 * k, N) == 1:\n"
               "            return r0 * k\n")
        self.assertEqual(G.scan_source(src, "all"), [])
        src_range = src.replace("(1, 2, 3, 4)", "range(1, 5)")
        self.assertEqual(G.scan_source(src_range, "all"), [])

    def test_large_or_variable_range_is_still_flagged(self):
        base = ("def build_x(a, N):\n"
                "    for r in {it}:\n"
                "        if pow(a, r, N) == 1:\n"
                "            return r\n")
        for it in ("range(1, N)", "range(1, 100)", "range(1, 10 ** 6)", "range(N)", "list(range(1, 5))"):
            self.assertTrue(G.scan_source(base.format(it=it), "all"), it)

    def test_builder_calling_classical_period_is_flagged(self):
        src = "def build_x(a, N):\n    return classical_period(a, N)\n"
        self.assertTrue(G.scan_source(src, "builders"))

    def test_builders_mode_ignores_non_builder_functions(self):
        src = CLEAN + ("\ndef classical_period(a, n):\n"
                       "    for r in range(1, n):\n"
                       "        if pow(a, r, n) == 1:\n"
                       "            return r\n")
        self.assertEqual(G.scan_source(src, "builders"), [])
        self.assertTrue(G.scan_source(src, "all"))   # the same code is caught when everything is checked

    def test_syntax_error_is_not_swallowed(self):
        with self.assertRaises(SyntaxError):
            G.scan_source("def (:\n", "all")


class GuardOnTheRealCode(unittest.TestCase):
    def test_real_builder_modules_are_clean(self):
        self.assertEqual(G.scan_all(), [])

    def test_guard_is_not_vacuous(self):
        text = (G.ROOT / "notebook/shors_demo.py").read_text(encoding="utf-8-sig")
        names = G.builder_functions(text)
        for expected in ("build_shor_circuit", "c_amod15", "controlled_modmul_gate",
                         "build_shor_circuit_n21"):
            self.assertIn(expected, names)
        self.assertNotIn("classical_period", names)

    def test_q2_module_is_guarded(self):
        self.assertEqual(G.discover_guarded()["src/q2_arith.py"], "all")


if __name__ == "__main__":
    unittest.main()
