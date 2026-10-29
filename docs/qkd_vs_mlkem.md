# QKD (BB84) vs ML-KEM-768 for key establishment

| Property | ML-KEM-768 (FIPS 203) | BB84 QKD (our Q6) |
|---|---|---|
| Quantum computing involved? | No: classical, quantum-resistant | Yes in the protocol; here simulated on Aer, toy size |
| Hardware | ordinary computers | dedicated optical hardware and a quantum channel in real life |
| Security basis | lattice problem hardness (computational) | physics (no-cloning), with an authenticated classical channel |
| Classical channel | none needed | must be authenticated (we use ML-DSA-65) or a man-in-the-middle works |
| Key / blob size | pk 1,184 B, ciphertext 1,088 B | no KEM ciphertext; key from sifting plus privacy amplification |
| Eavesdropper detection | none (relies on hardness) | QBER near 25% for intercept-resend; abort above threshold |
| Recommendation for our projects | YES, software-only default | demonstration only, not a replacement for ML-KEM here |

All QKD numbers: Aer simulator, toy size. Simulator output is pseudo-random.
