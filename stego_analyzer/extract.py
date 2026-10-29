"""Stage 3: extract the blob.  Owner: Vaibhav (written in Week 6, please review).

Calls the pinned image project's own extractor BY PATH (data/targets/final-year-part1/lsb_stego.py,
function extract_lsb, the one extras/stego_attack_toy.py uses). The pinned repository is never edited.
Only the plain LSB format is covered. Other formats (the R-channel module, XOR-LSB) are not extracted
here, so the pipeline reports them as "unrecognised".

Not yet run against the real pinned code by the person who wrote it: tests use a stand-in module.
"""
import importlib.util
from pathlib import Path

from . import toyformat

ROOT = Path(__file__).resolve().parent.parent
PINNED_DIR = ROOT / "data" / "targets" / "final-year-part1"
SOURCE = "final-year-part1/lsb_stego.py extract_lsb, called by path"


def load_pinned_extractor(pinned_dir=None):
    """The pinned project's extract_lsb function."""
    file = Path(pinned_dir or PINNED_DIR) / "lsb_stego.py"
    if not file.is_file():
        raise FileNotFoundError(f"pinned image project not found at {file}: run git submodule update --init")
    spec = importlib.util.spec_from_file_location("pinned_lsb_stego", file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.extract_lsb


def read_hex(image_path, pinned_dir=None):
    """The hex text the pinned extractor reads from the image, or None if it is not a hex payload."""
    try:
        text = load_pinned_extractor(pinned_dir)(str(image_path))
    except FileNotFoundError:
        raise
    except Exception:                      # the extractor failed on this image: nothing sensible is hidden
        return None
    text = text.strip() if isinstance(text, str) else ""
    return text if toyformat.is_hex(text) else None


def extract(image_path, method, pinned_dir=None):
    """Return {"ok": bool, "blob": bytes, "source": str}. The blob is the extracted hex text as ASCII bytes."""
    from . import NotImplementedStage
    if method != "lsb":
        raise NotImplementedStage(f"extract ({method} is not covered)")
    text = read_hex(image_path, pinned_dir)
    if text is None:
        return {"ok": False, "blob": b"", "source": SOURCE}
    return {"ok": True, "blob": text.encode("ascii"), "source": SOURCE}
