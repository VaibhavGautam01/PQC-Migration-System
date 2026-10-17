"""
run_tests.py - run ALL project tests with one command.

Runs the tests in tests/ and in notebook/ (qubit estimator and Shor's demo).

Usage:  python run_tests.py
Exit code: 0 if every test passes, 1 if a test fails or none are found,
so the script can be used from other scripts and pre-commit checks.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent

# Every folder that holds test_*.py files. notebook/ is here because its
# tests import modules that live next to them (qubit_estimator, shors_demo).
TEST_DIRS = [ROOT / "tests", ROOT / "notebook"]


def main() -> int:
    """Discover and run every test_*.py file in TEST_DIRS.

    Returns:
        0 if all tests passed, otherwise 1.
    """
    # Project root on sys.path so tests can import project modules.
    sys.path.insert(0, str(ROOT))

    # One suite per folder, combined into a single run.
    suite = unittest.TestSuite()
    for folder in TEST_DIRS:
        suite.addTests(unittest.defaultTestLoader.discover(
            start_dir=str(folder),
            pattern="test_*.py",
            top_level_dir=str(folder),
        ))

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    # Guard: "no tests found" must be a failure, not a false success.
    if result.testsRun == 0:
        print("ERROR: no tests found. Check tests/, notebook/ and the test_*.py names.")
        return 1

    return 0 if result.wasSuccessful() else 1


# Run only when executed directly, not when imported.
if __name__ == "__main__":
    sys.exit(main())
