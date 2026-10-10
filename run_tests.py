"""
run_tests.py - Stage 1 ka unified test runner (Issue #2)

Kaam: scanner.py aur edge_cases.py ke saare tests ek hi command se chalana.
Usage: python run_tests.py
Exit code: 0 = saare tests pass, 1 = koi test fail (CI/pre-commit mein kaam aata hai)
"""
import sys
import unittest
from pathlib import Path

# Is file ke saath wale "tests" folder ka absolute path.
# Path(__file__) use karne se script kisi bhi folder se chalao, path sahi rahega.
TESTS_DIR = Path(__file__).parent / "tests"


def main() -> int:
    # Project root ko sys.path mein daalo taaki tests mein
    # "from scanner import ..." jaise imports bina error ke chalein.
    sys.path.insert(0, str(Path(__file__).parent))

    # Discovery: tests/ ke andar "test_*.py" naam ki saari files apne aap dhundh lega.
    # Naya test file add karne par is script ko badalna nahi padega.
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(TESTS_DIR),
        pattern="test_*.py",
    )

    # verbosity=2 -> har test ka naam aur PASS/FAIL line-by-line dikhega,
    # debugging aur demo dono ke liye useful.
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    # Guard: agar 0 tests mile to ise fail maano.
    # Warna galat folder/naming ki wajah se "0 tests passed" jhoothi success dikhayega.
    if result.testsRun == 0:
        print("ERROR: koi test nahi mila. tests/ folder aur test_*.py naming check karo.")
        return 1

    # wasSuccessful() sirf tab True hota hai jab koi failure ya error na ho.
    return 0 if result.wasSuccessful() else 1


# Sirf direct run karne par chale, import karne par nahi.
if __name__ == "__main__":
    sys.exit(main())
