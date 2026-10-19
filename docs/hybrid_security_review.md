# Security Review: hybrid ML-KEM-768 + AES-256-GCM

Reviewer: Yatharth Raghuvanshi. Author of the module: Uday Pratap Singh. # type: ignore
File reviewed: `pqc_stego/hybrid.py` at commit <hash>. # pyright: ignore[reportUndefinedVariable]
Tool: `src/hybrid_review.py` (static scan plus dynamic checks).
Library caveat: kyber-py and dilithium-py are educational and not hardened
against timing attacks. This is a prototype review, not a production audit.

## Automated results

<paste the table printed by `python src/hybrid_review.py`>

## Manual checklist

| Item | Status | Evidence |
|---|---|---|
| Fresh random 96-bit nonce per message | <pass / fail / not checked> | <line or test> |
| HKDF-SHA256, 32-byte output, fixed info string, salt documented | <...> | <...> |
| KEM ciphertext and version bound as AAD | <yes / no (recommended)> | <...> |
| ML-KEM-768 from the FIPS 203 class | <...> | <...> |
| Encapsulation-key validation | <by library / by code / missing> | <...> |
| One generic error; no plaintext before tag check | <...> | <...> |
| Caller writes nothing on failed decrypt | <...> | <...> |
| Secret key not logged or committed | <...> | <...> |
| Only os.urandom / get_random_bytes for randomness | <...> | <...> |
| Library versions pinned | <...> | <...> |
| Maximum message size | <...> | <...> |
| Sizes match FIPS 203 (pk 1,184; ct 1,088; sk 2,400) | <...> | <...> |

## Findings

| ID | Severity | Finding | Owner | Status |
|---|---|---|---|---|
| <F1> | <high / medium / low> | <what, where, why it matters> | Uday | <open> |

Write "None found" only if that is true.

## Not covered

- Timing and side channels (pure Python, educational library).
- Memory handling of secrets (Python cannot reliably wipe memory).
- The correctness of the ML-KEM implementation itself.
- The static scan is heuristic and finds obvious patterns only.

## Conclusion

<one or two sentences: what is safe to demonstrate, what must be fixed first>