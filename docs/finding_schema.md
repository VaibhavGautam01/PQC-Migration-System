# Finding schema (interface contract, frozen Day 2)

Every detector returns a list of findings. A finding is a plain dict.

## Detector interface

    detect(rel_path, text) -> list[finding]

Detectors are registered per file extension with `register(ext, fn)` in
`src/scanner.py`. `scan_file()` calls every detector registered for the
file's extension and then adds the contract fields below.

## Entry points

- `scan(path, options=None) -> ScanResult` : folder or file, with filters.
  `ScanResult` has `findings`, `files_scanned`, `files_skipped`, `errors`, `seconds`.
- `scan_path(root) -> list` : old list-returning wrapper, used by `run_all.py`.
- `scan_file(path, root) -> list` : one file.

## Contract fields

| Field | Type | Meaning |
|---|---|---|
| project | str | Set by the pipeline (repo name), not by the scanner. |
| file | str | Path relative to the scan root, forward slashes. |
| line | int | 1-based line number. |
| language | str | From the file extension (python, java, javascript, ...). |
| primitive | str | RSA, ECC, DSA, DH, AES, SHA, ... |
| pattern_id | str | Id of the pattern or rule that matched. |
| usage_purpose | str | "unknown" for now. Filled from Day 11. |
| confidence | str | high / medium / low. |
| key_size | int or null | Bits, if found. |
| snippet | str | The matching line, at most 200 characters. |
| flags | list[str] | Weakness flags. Empty for now. Filled from Day 12. |

## Planned (not yet in the output)

- `key_size_source`: literal, resolved_constant, inferred, unknown. Day 4.
  Today the scanner writes `size_basis` (free text); it is renamed or mapped on Day 4.

## Legacy fields (kept, other modules use them)

`description`, `modulus_bits`, `size_basis`, `is_default`.

Do not remove or rename them without updating the mapper, CBOM and tests.

## Rules

- Adding a field is fine. Removing or renaming one needs a test update.
- Paths always use forward slashes so output is the same on Windows and Linux.
- Uploaded code is never executed. Detectors only read text.