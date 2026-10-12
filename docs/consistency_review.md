\# Repository Consistency Review



Reviewer: Vaibhav Gautam. Issue #10. Reviewed against main at 71e7c18.



\## Checked and consistent



\- No Python cache files are tracked (`git ls-files | findstr /i "pycache .pyc"` prints nothing).

\- Test count: README.md and docs/final\_report.md both state 282 tests, matching a fresh run (282 tests, OK, with pytest installed).

\- The 31-bit and 95-bit attack results are labelled as local small-key snapshots, not pinned-commit results, in docs/final\_report.md, docs/edge\_case\_validation.md and (after this review) docs/padding\_weaknesses.md.

\- Stray backslashes pasted into four review documents were removed (edge\_case\_section.md, padding\_weaknesses.md, mapper\_review.md, risk\_report\_review.md), so lists and file names render correctly.

\- Citations present: Beauregard (2003) for the 2n+3 formula and Gidney and Ekera (2021) for RSA-2048 resource estimates (README.md, docs/cbom.md).



\## Removed during this review



\- Two duplicate clones at the repository root (Final-Year-project-part1 and Secure-Video-Steganography). They were untracked and held no local changes. The pinned copies used by the pipeline are in data/targets/.

\- A stray untracked file holding an outdated copy of risk\_report.md.



\## Open items for the file owners



1\. docs/final\_report.md line 71 still says "about 8 bits" for the R-channel module; the code comment only supports "n < 256" (Tarun). docs/week1\_summary.md line 33 says the same.

2\. docs/risk\_report.md has a 32-bit row for the image project in the physical-qubit table. That size comes from the small-key local copy, not from the pinned code (Tarun / Yatharth).

3\. docs/week2\_summary.md lists the 256/8/31-bit and 1024/2048-bit questions as open; docs/final\_report.md settles them (Uday).

4\. requirements.txt should list pytest, because tests/test\_quantum\_mapper.py imports it (not re-checked here).



\## Known limits



\- The commit-message check finds missing issue numbers, not wrong ones (see docs/commit\_reference\_check.md).

\- The attack demonstrations were not repeated on the pinned commits.

