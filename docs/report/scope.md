# Scope paragraph for the final report

Status: draft for the final report, Week 5. Items marked CONFIRM WITH SIR are not decided yet and must be
settled before this text is final. Every number below names what it was measured on.

## The paragraph

This project analyses two target repositories, an image steganography project (Final-Year-project-part1, pinned
at commit bb6d944) and a video steganography project (Secure-Video-Steganography, pinned at commit 4514806).
The scanner found 31 cryptographic findings in them (RSA 30, SHA-256 1; measured on commit 68d92a2), and every
finding was matched to its real source line (31 of 31). On the 33 crypto lines that the team labelled by hand in
these two repositories, precision is 31 of 31 (100 percent) and recall is 93.9 percent (100 percent when the two
insecure-random flags are counted); the label set is small and was made by the team, so these two numbers do not
say how the scanner performs on other code.

On top of the scan we built a risk score for these two projects only. It is a transparent weighted score from 0 to
100 with six factors, weights version v1.0, split by layer (message encryption, frame-selection key, integrity),
with the quantum part and the classical part shown separately and a range from a sensitivity study and from three
scenarios for the years until a large quantum computer exists. It is not a probability. For the image project the
message-encryption layer moves from 91.9 (Critical, 256-bit key in the code) to 4.7 (Low) when textbook RSA is
replaced by ML-KEM-768 with AES-256-GCM; for the video project the project score moves from 64.1 (High) to 29.8
(Moderate) at a 2048-bit key. The video figure is a lower bound on the improvement: the model has no factor for
the strength of a frame-selection key, so the fix to that layer is not credited. The hiding layer (LSB embedding)
is measured by steganalysis and is not part of the score.

The migration prototypes (hybrid ML-KEM-768 + AES-256-GCM, optional ML-DSA-65 signing) use pure-Python,
educational libraries and are not production cryptography. At the time of writing they run on a reference
embedding backend written by the team, not on the pinned projects' own code. CONFIRM: update this sentence when
the pinned backends and the two patches are done.

All quantum results come from the Aer simulator at toy size (Shor for N = 15, 21 and 35 as phase estimation and
as a gate-level circuit with 2n+3 qubits, Grover on a toy cipher, BB84 and a random-number generator). Every Shor
and Grover run has a saved record in the evidence format; the BB84 and random-number records are still being
converted to that format. Nothing here shows that RSA-1024 or RSA-2048 can be broken today; numbers for real key sizes
are published estimates and are labelled as estimates. ML-KEM, ML-DSA and AES-GCM are classical algorithms that
resist quantum attacks; they do not use a quantum computer.

The Stego Analyzer takes a stego image as input, breaks it where a method applies, and then runs the full
pipeline. Sir agreed this flow on 22 October 2026. What it covers today is narrow, and the report must say so.
It reads the plain LSB format of our image project through the pinned project's own extractor. The image does
not carry the RSA modulus, so breaking an RSA payload needs the public key (N, e) together with the image; this
matches the attacker in our model, who holds the stego file and the public key. Sir confirmed on 27 October 2026 that the public
key is a second input. For a toy-size key (N up to 35) it factors N with the gate-level Shor circuit on the Aer
simulator, saves an evidence record for every run, and recovers the message. For larger keys it gives a labelled
estimate (2n+3 logical qubits and the published figure) and never a time. An ML-KEM + AES-GCM payload is reported
as "resists", and anything else, including the image project's R-channel module and the video project's
XOR-LSB, is reported as "unrecognised". RSA payloads of real size are not attacked, and the small-key attack for
mid-size moduli is not built yet. Sir accepted this limit on 27 October 2026. CONFIRM WITH SIR: whether the R-channel module or the video
formats must be covered. On the generated test set of 6 images made by
our own project (three toy RSA keys, one RSA image without the key, one ML-KEM image, one clean cover) the analyzer
gave the expected result for all 6; the set is small, it was made by the same team, and the numbers say nothing
about images from other tools. Accuracy on other tools' images is unknown.

## What the approval deck promised and what was delivered

| Deck promise | Delivered | Evidence |
|---|---|---|
| Scanning Python code | Yes, on two repositories | 31 findings, line check 31 of 31 |
| Scanning Java and JavaScript | Not delivered. The scanner reads .java and .js files, but no Java or JavaScript repository was scanned or measured | none; we claim no result |
| Fine-tuned LLM classifier | Not delivered | none |
| 20 or more repositories | 2 repositories | data/targets |
| More than 90 percent precision | Measured on the two repositories only: precision 100 percent, recall 93.9 percent | src/validate_ground_truth.py, data/ground_truth.json |
| PDF and CSV export | Delivered for the findings | scripts/export_findings.py |
| Stego Analyzer (image in, break, then the pipeline) | Delivered for plain LSB images of our image project; toy-size keys broken with a real Shor circuit on the simulator, estimates for larger keys, public key needed. Not delivered: R-channel and video formats, the small-key attack | stego_analyzer/, scripts/analyzer_testset_run.py |
| Quantum risk percentage for a project | Delivered for the two target projects only (sir agreed to this limit) | outputs/risk_scores.json |

CONFIRM WITH SIR: his view on the four deck items marked "not delivered" or "2 repositories". The deck must not
be quoted as delivered for them until he has said how he wants them treated.

## Open items before this text is final

1. Sir's answer on Java, JavaScript, the LLM classifier and the repository count.
2. Sir's answer on whether the R-channel module or the video formats must be covered by the Analyzer (the public
   key input and the limit were accepted on 27 October 2026).
3. Pinned backends and the two patches (then remove the reference-backend sentence).
4. Re-check every number in this file against code output (python scripts/repo_check.py and run_pipeline.py).
