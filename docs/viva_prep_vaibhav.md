# Viva prep: Vaibhav's work (Attack Evidence and Validation)

Every answer below is checked against code you ran and numbers you measured in this
conversation. Where a number is quoted, it is the real output from your machine, not an
estimate. Use these as your base; practice saying them in your own words.

## Q1 — Shor's algorithm (phase estimation)

**"Your Shor run is on a simulator. What did it prove, and what did it not prove?"**
It proved the circuit — Hadamards, controlled modular-multiplication unitaries, inverse QFT,
measurement — correctly finds the period of a^x mod N *from measured outcomes only*, for
N = 15, 21, 35, with every factor verified by a gcd step and cross-checked against an exact
statevector calculation (max difference ~1e-14). It did **not** prove the algorithm is fast:
the controlled-U gates are built as dense matrices (`pow(a, 2**j, N)`), so the circuit does
not scale — that's explicitly why Q4's resource estimates use the Q2 gate-level circuits
instead of Q1's.

**"Why does N=15 prove little on its own, and what did you do about it?"**
A circuit "compiled" just for N=15 can bake the answer into its gate structure (Smolin,
Smith and Vargo, 2013) and prove almost nothing. You ran the *same* generic code — unchanged
— on N=15, 21 and 35, with different bases a, and it gave the correct, different answer each
time (periods 4, 6, 12; factors 3×5, 3×7, 5×7). That's the "change the question" test
(rule 6): one circuit builder, multiple genuine questions, no hard-coded shortcuts.

**"How do you know there's no classical shortcut hidden in your circuit?"**
Three things: the static guard scans `q1_shor_pe.py` and `q1_run.py` for period-search loops
and factoring-library imports and passes; `pow(a, 2**j, N)` is the one classical call allowed,
because it only builds the oracle the algorithm is given, not the answer; and the period and
factors are read only from `shor_post.py`'s post-processing of the *measured* counts
(continued fractions, then gcd) — never computed independently and compared.

**"What's the chi-square test for, and what did you get?"**
It compares your measured histogram against the theoretical distribution of outcomes for a
true quantum circuit. p-values of 0.069 (N=15), 0.217 (N=21), 0.496 (N=35) — all well above
the 0.01 cutoff — mean the measurements are statistically consistent with theory, i.e. the
circuit behaves like the real algorithm predicts, not like noise or a shortcut.

## Q3 — Grover's algorithm on a toy cipher

**"How do you know your Grover oracle doesn't already contain the answer?"**
The oracle is built only from the two public (plaintext, ciphertext) pairs, using X/CNOT/
Toffoli gates that compute the toy cipher and then uncompute it — no function in
`q3_grover.py` takes a key, checked by both the static guard and an AST scan that bans
importing the classical cipher module into the builder file. The oracle was verified by
truth table against the classical cipher for every key and several plaintexts (0 mismatches
out of 256 keys × 5 plaintexts), using an independent numpy emulator — a second, separately
written simulation method (rule 9).

**"Why two known pairs, not one?"**
With this toy cipher, one 8-bit pair can be satisfied by more than one key (you measured
cases with 1, 2 and 3 matching keys from a single pair). Two pairs narrow it to exactly one
key for all 256 possible secrets — confirmed by exhaustive check.

**"Does Grover break AES-256?"**
No — it halves the *effective* security to about 128 bits, which is still infeasible. This
toy demonstration (8-bit key, 256 candidates, ~12 optimal rounds) shows the algorithm's
sin²-curve behaviour is real; real AES-256 sizes are covered only by published resource
estimates, never by this circuit.

**"What did your sweep actually show?"**
Success probability measured at 0, 2, 4 … 24 rounds rose to ~1.0 at the theoretical optimum
(k=12 for one matching key) and *fell again* past that point — the classic Grover overshoot.
All three test keys (183, 42, 250) were found and verified at k=12 with no code change
between them.

## Q11 — Quantum counting

**"Why do you need counting before you search?"**
Grover's optimal round count depends on M, the number of matching keys — but a real attacker
usually doesn't know M in advance. Guess wrong and the success probability can collapse (an
"overshoot" with too many rounds, or undershoot with too few). Quantum counting — phase
estimation applied to the Grover operator itself — measures M *before* any search runs.

**"Is the key ever given to the counting circuit?"**
No. The circuit sees only the public (plaintext, ciphertext) pair and the attacker's already-
known key bits; the count (and later the key) comes only from measurement. The static guard
and an import-ban check (no `toy_cipher`, no `counting_theory` inside the builder) confirm
this the same way as Q3.

**"What's special about the controlled Grover operator here?"**
Only two gates genuinely need the extra control qubit: the one that *sets* the oracle's match
flag (everything else cancels when the control is 0), and the diffusion step's final
multi-controlled-Z (with a Z on the control qubit afterwards, to remove a stray global phase
that would otherwise shift the measured count). This keeps controlled-G efficient instead of
naively controlling every gate.

**"Did it actually estimate the right count?"**
Yes — verified in the numpy emulator against the analytic theory to ~1e-14, and the maximum-
likelihood estimator (`estimate_count_ml`) recovered M = 1, 2 and 3 correctly from ideal
counting histograms, doing better than simply rounding the most frequent outcome when the
counting register is small.

## Attacks and evidence (image, video, "break our own work")

**"Your PQC image attack passed 12 of 12 checks. What does that actually prove?"**
That for this construction (ML-KEM-768 + AES-256-GCM, LSB-hidden), an attacker with *only*
the stego image and the public key cannot: read the plaintext, decrypt with a different
secret key, or tamper with any part of the blob (KEM ciphertext, nonce, tag, AES part)
without the receiver's decryption failing loudly. It does **not** prove ML-KEM itself is
secure — kyber-py is an educational library, not hardened, and the libraries are explicitly
noted as a production risk in the plan.

**"Why does extraction still succeed if the encryption is fixed?"**
Because the LSB hiding layer is keyless — anyone can pull bytes out of the image's LSB plane,
with or without the key. Migration replaced the *encryption* layer; it never claimed to fix
the *hiding* layer. That's explicitly called out as the remaining weakness in every attack
script's output.

**"What did the video attack add beyond the image one?"**
Signing. All 12 checks passed against the real `video_pqc.py` and `signing.py`, including the
one that matters most: verifying a signed video with the *wrong* signer's public key is
correctly rejected (`SignatureError: signature does not verify`) — confirming ML-DSA-65
genuinely checks key correspondence, not just signature format.

**"What did 'breaking your own work' turn up?"**
A reused AES-GCM nonce leaks the XOR of two plaintexts with no key needed (the classic
two-time-pad weakness) — but `hybrid_encrypt()` itself never reuses one (2000/2000 distinct
nonces, `os.urandom` every call), so this doesn't apply to the real code, only to a
hypothetical misuse. Two honest limits of the risk model: mislabelling a layer's category or
exposure can swing its score by 70-95 points with zero change to the real crypto, because the
model trusts the labels it's given rather than re-deriving them from raw code; and
`risk_weights.json` has no integrity check, so a one-line edit can zero out a factor.

**"Is the risk percentage a probability?"**
No — it's a transparent weighted score, and your own gaming checks are part of the evidence
for that: a score can move by dozens of points through a labelling choice alone, which a real
probability could never do.

## Day 1/2 loose ends (lower priority, check with Tarun/Yatharth first)

- **"Run the toy stego attack with the largest N Q1 or Q2 handles."** You've run Q1 up to
  N=35 (18 qubits) via the `--shor` flag on `stego_attack_toy.py`. Ask Yatharth what N his Q2
  gate-level circuit reaches (the plan's stretch goal is an 8-bit N like 221) — if his is
  larger, re-run the toy attack against *that* N once his code is merged, and note the result
  in the evidence doc.
- **256-bit sieve stretch goal:** not attempted. If time doesn't allow it, write exactly that
  in the report — "not completed" — rather than guessing a time.
- **Q8 (IBM hardware):** needs a real IBM Quantum account and confirmed runtime access/limits
  (the plan notes an Open Plan showed up to 10 minutes/month when last checked). This is a
  team decision for Tarun to confirm, not something to do unilaterally.

## v3 additions - Stego Analyzer questions (Section 16, new in this version)

**"Can your tool break any stego image?"**
No. Only images from our two projects' own formats (LSB and XOR-LSB hiding; textbook RSA,
OAEP-style and ML-KEM+AES-GCM payloads). Anything else is reported as "unrecognised" - never
guessed. The Shor stage only runs at toy size (reusing Q2's circuit); larger moduli get a
labelled 2n+3 estimate, never an actual break and never a time-to-break claim.

**"How does the analyzer decide which technique was used?"**
Two separate, independent steps, neither guessing: the HIDING method comes from steganalysis
features (ones fraction, chi-square, header scan) already used elsewhere in this project; the
CIPHER comes from the blob's own structure (modulus size for textbook RSA, OAEP padding
structure, or the 1,088-byte ML-KEM ciphertext prefix for the hybrid blob). If neither matches
a known structure, the result is "unrecognised", stated plainly, with the test-set accuracy
quoted rather than a confidence claim with no backing number.

**"How do you know the analyzer's Shor stage is real and not a shortcut?"**
It calls the Q2 gate-level circuit builder with the modulus N read out of the actual uploaded
image - never computed classically first. The same static guard (rule 8) that scans every
other circuit builder in this project covers this file too, and the change-the-question test
(rule 6) is run with two different uploaded images carrying two different N values, confirming
the same code gives two different, correct answers.

**"Why does the analyzer say 'resists' for an ML-KEM image?"**
Extraction still works (the LSB hiding layer stays keyless regardless of what's encrypted
inside), but there is nothing to factor: an ML-KEM public key is lattice data, not an integer
modulus. AES-256-GCM is only Grover-weakened to about 128 effective bits, which is not a break
at this size. "Resists" names exactly these two facts, not a guess.

**Test-set generation note (Week 5 Day 1, extras/generate_test_set.py)**
A real bug was caught and fixed while building the test-set generator: a Python closure
pitfall (`lambda: f(n) for n in values`, which silently uses only the LAST value of `n` for
every lambda) caused every requested toy modulus to collapse into just one. Caught by testing
output, not by code review - a reminder for the analyzer's own test-set generation code to be
checked the same way, not trusted by inspection alone.
