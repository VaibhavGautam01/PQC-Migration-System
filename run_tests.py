"""
run_tests.py - run all Stage 1 tests with one command (Issue #2).

Usage:  python run_tests.py
Exit code: 0 if every test passes, 1 if a test fails or none are found,
so the script can be used from other scripts and pre-commit checks.
"""
import sys
import unittest
from pathlib import Path

# Absolute path of the "tests" folder next to this file. Using __file__
# makes the script work no matter which folder it is started from.
TESTS_DIR = Path(__file__).parent / "tests"


def main() -> int:
    """Discover and run every tests/test_*.py file.

    Returns:
        0 if all tests passed, otherwise 1.
    """
    # Put the project root on sys.path so tests can import project modules.
    sys.path.insert(0, str(Path(__file__).parent))

    # Discovery picks up every "test_*.py" file in tests/, so adding a new
    # test file never requires editing this script.
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(TESTS_DIR),
        pattern="test_*.py",
    )

    # verbosity=2 prints each test name with ok/FAIL, useful for debugging
    # and for demos.
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    # Guard: treat "no tests found" as a failure. Otherwise a wrong folder
    # or file name would report a false "0 tests passed" success.
    if result.testsRun == 0:
        print("ERROR: no tests found. Check tests/ and the test_*.py names.")
        return 1

    # wasSuccessful() is True only when there are no failures or errors.
    return 0 if result.wasSuccessful() else 1


# Run only when executed directly, not when imported.
if __name__ == "__main__":
    sys.exit(main())
