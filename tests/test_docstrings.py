"""Guard: every public function in quantum_mapper.py must have a docstring (Issue #5)."""

import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import quantum_mapper as qm  # noqa: E402


class TestDocstrings(unittest.TestCase):
    def test_module_has_docstring(self):
        self.assertTrue(qm.__doc__ and len(qm.__doc__) > 100)

    def test_every_public_function_is_documented(self):
        for name in qm.__all__:
            obj = getattr(qm, name)
            if inspect.isfunction(obj):
                with self.subTest(function=name):
                    self.assertTrue(inspect.getdoc(obj), f"{name} has no docstring")

    def test_all_exports_exist(self):
        for name in qm.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(qm, name))


if __name__ == "__main__":
    unittest.main()
