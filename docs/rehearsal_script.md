# Rehearsal script: demo of the risk system (about 12 minutes, then questions)

Week 5. Run the whole path twice before the real demo and fix anything that fails. Every number below was taken
from a command or file in this repository; if a number on screen is different, trust the screen and fix this file.
Everything quantum is "Aer simulator, toy size".

## Before the demo (5 minutes, not shown)

    git checkout main
    git pull
    git submodule update --init
    python run_pipeline.py --project both
    streamlit run src/live_dashboard.py

The pipeline must end with "RESULT: PIPELINE OK, outputs bilkul same, tests pass." Do not press the Pipeline page
buttons during the demo: Scan, Rebuild CBOM and Full pipeline are switched off until the box is ticked.

## The path

| # | Minutes | Page | Say | Show (expected on screen) |
|---|---|---|---|---|
| 1 | 1 | Overview, Findings | "We scanned two projects and found 31 places that use cryptography." | 31 findings: RSA 30, SHA-256 1. Every finding was checked against its source line, 31 of 31. |
| 2 | 2 | Risk score | "The percentage is a weighted score, not a probability. Every weight is in one file." | Image project 91.9 (Critical); video project 64.1 (High). Range over the three Z scenarios: image 86.7 to 96.4, video 59.8 to 67.7. Open the factor breakdown. |
| 3 | 1.5 | Risk score, qubit cost | "The qubit cost uses 2n+3 logical qubits. We also measured real circuits." | 2048 bits: 4,099 logical qubits, F2 score 46.2. Measured circuits for n = 4 to 8 use exactly 2n+3 qubits. The 20,000,000 physical qubits figure is a published estimate and is marked as one. Extrapolation row says "not available yet" (until Yatharth's fit exists). |
| 4 | 2 | Before and after | "Same engine before and after the migration." | Image: 91.9 to 4.7 (Low), ML-KEM-768 + AES-256-GCM. Switch to Video: 64.1 to 29.8 (Moderate). Say: "L2, the frame key, is not credited, so this is a lower bound; the header scan still finds the frames." |
| 5 | 1 | PQC advisor | "Layer by layer: what to use and why." | L1 ML-KEM-768 + AES-256-GCM, L2 256-bit random key, L3 the AES-GCM tag, L5 optional ML-DSA-65. Sizes table. "ML-KEM is classical; it is quantum-resistant, not quantum." |
| 6 | 3 | Quantum Lab | "Real circuits on a simulator, with a record for every run." | Evidence table. Shor N = 15, 21, 35 at gate level: 11, 13 and 15 qubits, success 60, 80 and 85 percent on 20 shots. Grover on a toy cipher. Evidence gate and static guard cards. "Simulator, toy size: this does not show RSA-2048 is broken." |
| 7 | 1.5 | Migration demo | "The recommended migration really runs." | Keep the message "PQC!" and press "Run the comparison". Textbook RSA gives the same ciphertext twice, and an attacker with only the public key factors the tiny modulus and reads the message (a classical attack on a small key; at real sizes this is Shor's job). ML-KEM-768 + AES-256-GCM: a wrong private key fails to decrypt. "Educational library, not production crypto." |

## Stego Analyzer segment (3 minutes, add after the Migration demo once the pinned test set exists)

Before the demo: python scripts/make_analyzer_testset.py, then python scripts/analyzer_testset_run.py (about 1 minute).
Say what it measured, on our own images only. If the pinned project is not checked out, skip this segment and say
the Analyzer is built but not demonstrated.

| Step | Do | Expected |
|---|---|---|
| 1 | Page "Stego Analyzer", upload toy_rsa_N15.png, enter N = 15, e = 7 | Result: broken toy. Message HELLO recovered. Label "Aer simulator, toy size". Risk 95.5 (Critical). Evidence table names the Shor run records. |
| 2 | Upload toy_rsa_N21.png with N = 21 and its e | Different factors (3 x 7), no code change. |
| 3 | Upload ml_kem_aes_gcm.png, no key | Result: resists. Risk 4.7 (Low). "Extraction works, nothing to factor." |
| 4 | Upload toy_rsa_N15.png with no key | Unrecognised: "modulus unknown, give the public key". Nothing is guessed. |
| 5 | Upload clean_image.png | Unrecognised. |
| 6 | Download the PDF | One page with the result, the label and "not a probability". |

Say: "It only handles images from our own project, and a real RSA-2048 key would give a labelled estimate, never a time."

## If something fails

| Failure | Do this |
|---|---|
| Dashboard will not start | python -m streamlit run src/live_dashboard.py; if it still fails show docs/final_dashboard.md and docs/risk_report.md |
| A page shows "file not found" | python run_pipeline.py --project both, then refresh the page |
| Quantum Lab is slow | Do not run anything live: the page only reads saved records |
| Shor demo page is slow | Skip the live run; show the saved runs and say they are saved |
| A number differs from this script | Say what is on screen, then fix this file after the demo |

## Questions to expect (answers must match the code)

1. **Is the percentage a probability?** No. It is a transparent weighted score with a sensitivity range; the
   weights are our choice and are not fitted to data.
2. **What does it depend on that you had to assume?** How long the data must stay secret (X = 5 years), how long a
   migration takes (Y = 2) and the years until a large quantum computer (Z = 10, with 5 and 20 as scenarios). Agreed
   with sir on 17 October 2026 and stored with the date in data/manual_facts.json.
3. **Is ML-KEM a quantum technology?** No. It is classical and quantum-resistant.
4. **Your Shor run is on a simulator. What did it prove?** That the algorithm works at toy size and that our circuit
   is built from gates (2n+3 qubits). It does not show that RSA-1024 or RSA-2048 can be broken today.
5. **How do you know the circuit does not contain the answer?** Static guard test, truth-table tests of every
   reversible block, and the change-the-question test: N changes and the result changes with no code change.
6. **Does Grover break AES-256?** No. It halves the effective bits to about 128. Real sizes come from published estimates.
7. **Why does the "after" score not reach zero?** The hiding layer is still weak (the header scan finds the
   frames), the model cannot credit the frame-key fix, and AES-256 keeps its Grover exposure.
8. **Why does showing the ciphertext not raise the score of an ML-KEM layer?** The exposure factor is gated by the
   layer's own weakness.
9. **What did the approval deck promise and what was delivered?** See docs/report/scope.md. Java, JavaScript and
   the LLM classifier were not delivered; we claim no result for them.
10. **Can your tool break any stego image?** No. Only images from our own formats. The Shor stage runs only at toy
    size; larger keys get a labelled estimate; other images are reported as unrecognised. (The Analyzer is built in Week 6.)
11. **Where does quantum computing appear and where does it not?** In the attacks (Shor, Grover) and in BB84 key
    distribution, all on a simulator. ML-KEM, ML-DSA and AES-GCM are classical.
12. **Are the prototypes production crypto?** No. kyber-py and dilithium-py are educational and not hardened
    against timing attacks; the production route is a native library such as liboqs-python.

## After each rehearsal

Write one line in docs/REHEARSAL_LOG.md: date, who ran it, what failed, what was fixed.
