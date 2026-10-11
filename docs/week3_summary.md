## Week 3 Summary: Cryptographic Bill of Materials (Uday)

**Goal:** turn the mapped findings into a CBOM that people can read and tools can parse.

**Delivered**

- **Schema** (`docs/cbom_schema.md`, `schemas/cbom.schema.json`): one entry per project, primitive and key size, with separate blocks for quantum risk, classical risk and padding risk, plus a PQC recommendation.
- **JSON CBOM** (`docs/cbom.json`) built by `src/cbom.py` from the mapped findings. Output is deterministic (no timestamps), so re-running it gives identical files.
- **Markdown CBOM** (`docs/cbom.md`), a table for human readers, with evidence, open data questions, notes and references.
- **Consistency check** (`python src/cbom.py ... --check`): verifies the JSON and Markdown files match each other and the source findings.
- Tests for the schema, builder, Markdown rendering and consistency check.

**Design decisions**

- Padding is never part of the quantum score. Textbook RSA is dangerous because it is deterministic, not because of Shor's algorithm.
- Small RSA keys are also a *classical* finding: moduli of 512 bits or less need no quantum computer, and anything under 2048 bits is below the minimum.
- Qubit estimates are logical qubits from the 2n+3 circuit and exclude error-correction overhead. Published physical-qubit estimates for RSA-2048 are far larger (Gidney and Ekera, 2021).
- Sizes carry a `size_status`. Entries whose size is `unverified` or `unknown` are listed under "Open data questions" instead of being presented as settled.
- RSA entries recommend ML-KEM-768 with AES-256-GCM (ML-KEM is a key-encapsulation mechanism, not a drop-in encryption algorithm).

**Still open:** the modulus-size questions from the Week 2 summary. Until the team confirms the overrides in `data/manual_facts.json`, the affected CBOM entries stay `unverified`.

**Limits:** all quantum work runs on a simulator at toy sizes; the CBOM reports estimates, not measurements.
