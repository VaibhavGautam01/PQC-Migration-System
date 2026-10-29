# Rehearsal: advisor and before/after (5 minutes)

## Path
1. Run the one command with --project both (write the exact command here after step 0 above).
2. Dashboard: Risk score page -> PQC advisor page -> Before and after page.
3. For L1: today (RSA, textbook) -> ML-KEM-768 + AES-256-GCM; show the score drop from the engine, not from memory.
4. Show the tamper test failing loudly, and the wrong-key test failing.

## Questions to answer from code, not from memory
- Is ML-KEM a quantum technology? No: classical, quantum-resistant, runs on ordinary computers.
- Why does the after score not reach zero? Name the exact residual factors and the hiding layer (measure, then write).
- Is the percentage a probability? No: a transparent weighted score with a sensitivity range.
- Why is the post-quantum payload easier to detect? 1,088 B KEM ciphertext plus nonce and tag; point to the steganalysis result.
- What did you simulate? Aer simulator, toy size; real-size results are published estimates, labelled as estimates.
- What is the status of NIST IR 8547? Final since 27 October 2026; deprecation after 2030, disallowance after 2035; guidance outside federal systems.
- Are your PQC libraries production-ready? No: educational, not hardened; liboqs-python is the production route.

## Failures seen in rehearsal (fill in honestly)
