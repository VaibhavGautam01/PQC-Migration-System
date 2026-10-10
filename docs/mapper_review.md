\# Peer Review: src/quantum\_mapper.py



Reviewer: Vaibhav Gautam. Author: Uday Pratap Singh. Issue #5.

Scope: read the module only; the unit tests were not reviewed.



\## What works well



\- Every public function has a docstring, and the module docstring documents input, output and limits.

\- `\_validate\_table()` fails fast if a primitive's family disagrees with the routing rule.

\- Unknown primitives are labelled UNKNOWN ("Manual review required") instead of being dropped.

\- The input is not modified, and all original fields are kept, so other fields pass through the mapper.

\- `modulus\_bits` is preferred over `key\_size`, matching the prime-size problem found in the image project.

\- AES and SHA are treated as weakened, not broken. Padding and classical key strength are kept out of the quantum score.

\- `load\_findings` accepts the combined findings.json layout from run\_all.py.



\## Checked by running the code



`canonical\_primitive()` returned: RSA -> RSA, AES-256-GCM -> AES, but RSA-2048, P256, ED448 and 3DES -> None (UNKNOWN).



\## Suggestions



1\. \*\*Unmapped names become UNKNOWN.\*\* Only the exact name `RSA` maps to RSA, so a name with a size suffix such as `RSA-2048` is UNKNOWN. ECC names such as P256 and ED448 are not covered, and neither are legacy ciphers such as 3DES (also Blowfish, RC4 and DES, which are not covered by the code). The scanner currently emits plain `RSA`, so there is no impact today. For legacy ciphers, an entry saying Grover applies and the cipher is classically weak would be more useful than "manual review".

2\. \*\*Grover wording for AES-128.\*\* "Reduced margin" may overstate the risk: NIST's post-quantum security category 1 is defined relative to AES-128 key search (verify against the NIST source before citing). Naive halving also ignores that Grover is hard to parallelise.

3\. \*\*Show `edge\_flag` in the mapping report.\*\* findings.json now carries the padding flag. A "Padding flag" column would let readers see it next to the quantum result, while keeping it out of the quantum score.



\## Questions for Uday



\- What does the SHA finding in the real findings.json show for size? The scanner's primitive is "SHA" with no size in the name, so inference may find none and report "Size unknown".

\- Do the unit tests cover the unmapped names above?

