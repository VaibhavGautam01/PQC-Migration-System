"""Stage 2: detect the hiding method.  Owner: Vaibhav (written in Week 6, please review).

For our own LSB format the test is a trial extraction with the pinned project's extractor: if it returns a
hex payload the image is "lsb", otherwise "clean_or_unknown". This recognises OUR format; it is not general
steganalysis and it does not claim a confidence. The error rate is measured on the generated test set by
scripts/analyzer_testset_run.py and must be quoted from there.

Formats that are not covered (the R-channel module, XOR-LSB) are reported as "clean_or_unknown", which the
pipeline turns into "unrecognised". The richer detector (ones fraction, chi-square, header scan on
realistic covers) is still to be built; extras/steganalysis_*.py hold the features.
"""
from . import extract


def detect(image_path, pinned_dir=None):
    found = extract.read_hex(image_path, pinned_dir) is not None
    return {"method": "lsb" if found else "clean_or_unknown", "confidence": None,
            "test_set_error_rate": None,
            "basis": "trial extraction with the pinned LSB extractor (our own format only)", "features": {}}
