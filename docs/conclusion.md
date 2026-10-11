### Impact

The pipeline turns a code scan into a prioritised migration plan. It finds classical cryptography in a codebase, maps each finding to the quantum algorithm that threatens it, estimates the logical-qubit cost for RSA findings, and records everything in a Cryptographic Bill of Materials with a PQC recommendation per component.

Three results matter most:

- **Public-key cryptography (RSA, ECC, DSA, DH) is the quantum-exposed part.** Shor's algorithm breaks it outright, so these findings carry the migration recommendation (ML-KEM-768 for key establishment, ML-DSA for signatures).
- **Symmetric cryptography (AES, SHA) is only weakened.** Grover's algorithm is a quadratic speed-up, not a break, so AES-256 and SHA-256 keep about 128-bit security.
- **Some of the most urgent problems are not quantum at all.** Textbook RSA with no padding is deterministic, and very small RSA moduli can be factored on ordinary hardware. The CBOM reports padding risk and classical key-strength risk separately from the quantum score so that they are not hidden behind it.

### Limitations

- All quantum work runs on a simulator at toy sizes. It shows that the algorithm works; it is not evidence that RSA-1024 or RSA-2048 can be broken today.
- Qubit figures are logical-qubit estimates from the 2n+3 circuit. They exclude error-correction overhead, and physical qubit counts are far larger. Published resource estimates for RSA-2048 (Gidney and Ekera, 2021) are the right reference for real-world numbers.
- The scanner is pattern-based. It can miss cryptography that is loaded dynamically or obfuscated, and it cannot read key sizes that are only decided at run time, so some sizes come from manual review. Findings whose size is unverified are labelled as such.
- Only two target repositories were analysed, so the results illustrate the method and do not support statistical claims.
- Recommendations are at algorithm level. No migration was performed on the target code, and performance and compatibility of the PQC algorithms were not tested.

### Future work

- Prototype a hybrid migration on one target project (ML-KEM-768 key establishment with AES-256-GCM) and measure the cost.
- Add scanner support for more languages and libraries, and run it in CI so new cryptography is caught as it is added.
- Export the CBOM in a standard format such as CycloneDX.
- Replace logical-qubit estimates with full resource estimates that include error correction.
