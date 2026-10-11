## Week 2 Summary: Mapper on real data (Uday)

**Goal:** connect `quantum_mapper.py` to the real `findings.json` and make the mapping report trustworthy.

**Delivered**

- The mapper now reads the real findings, validates them (`--strict`), and prefers `modulus_bits` over the scanner's `key_size`, because the scanner can report the prime size instead of the modulus size.
- Manual facts the scanner cannot see live in `data/manual_facts.json`. An override changes a size only when it is marked `confirmed`, so nothing disputed changes results silently.
- `docs/mapping_report.md` is generated from the real findings and ends with a **Data caveats** section that lists every size warning and unconfirmed override.
- Tests: synthetic ECC findings prove the mapper works beyond RSA; the real-data contract tests check `findings.json` against the agreed schema.
- Documentation: `docs/quantum_mapper.md` (mapping table, fields, commands, limits).

**Open questions (need a team decision before the CBOM is final)**

1. Modulus size for `Final-Year-project-part1`: the findings review says 256 bits (and under 256 as a number, about 8 bits, in `r_channel_stego.py`); the attack work reports a 31-bit modulus. These need to be reconciled and the overrides confirmed.
2. Default key size of `Secure-Video-Steganography`: 1024 or 2048 bits.

**Limits:** the mapping is theoretical (which attack applies, not that it is practical today). Padding and small-key weaknesses are reported separately from the quantum score. All quantum work runs on a simulator at toy sizes.
