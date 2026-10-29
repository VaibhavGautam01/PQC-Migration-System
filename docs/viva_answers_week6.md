# Viva answers (draft; check each answer against the code before the viva)

1. Is ML-KEM a quantum technology?
   No. ML-KEM, ML-DSA, SLH-DSA and AES-GCM are classical algorithms that resist quantum attacks. They run on ordinary computers.

2. Your Shor run is on a simulator. What did it prove, and what did it not prove?
   It proved the circuit finds a period from measured outcomes at toy size. It did not show scaling or break any real key.
   N = 15 proves little because a compiled circuit can bake the answer into its gates (verify the Smolin, Smith and Vargo 2013 citation before quoting). Q2 builds general modular arithmetic, so the same code runs for other N.

3. How do you know the Grover oracle does not contain the answer?
   It is built from the cipher's gates with two known pairs. A static guard test rejects search and factoring helpers, and the change-the-question test shows the output changes when the marked key changes, with no code change.

4. Does Grover break AES-256?
   No. It halves the effective strength to about 128 bits. Real-size claims cite published estimates, not our toy circuit.

5. Is the risk percentage a probability?
   No. It is a transparent weighted score from 0 to 100 with a sensitivity range. The weights are our choice and are not fitted to data.

6. Why does the "after" score not reach zero?
   The remaining score comes from factors that do not reach zero even for ML-KEM-768 + AES-256-GCM: F1 is 5 for NIST post-quantum algorithms, F4 is about 5 for AEAD, and the gated F5 and F6 follow them. In the worked reference case this gives about 4.7 % overall (confirm against the 'after' value in our before/after output). The hiding layer is outside the percentage and stays detectable: the larger payload, and in the video project the header scan

7. The approval deck promised Java, JavaScript and an LLM classifier. What did you deliver, and what did sir agree?
   See docs/report/scope.md for exactly what was delivered and what sir agreed. We claim no Java, JavaScript or LLM result that we did not measure (Plan v3, Section 1).

8. Where does quantum computing appear in your project, and where does it not?
   In attacks (Shor, Grover) and BB84, all on the Aer simulator at toy size. Not in ML-KEM, ML-DSA, AES-GCM, the risk score, or the analyzer's detection and identification.

9. What does the percentage depend on that you had to assume, and who agreed it?
   X = 5 years, Y = 2 years, Z = 10 years central with scenarios 5, 10 and 20, agreed with sir on 2026-10-17, stored in data/manual_facts.json.

10. Why does showing the ciphertext not raise the score of an ML-KEM + AES-GCM layer?
    F6 (exposure) is gated by the layer's weakness: F6_eff = F6 x max(F3, F4) / 100. A strong layer cannot be pushed up by exposure alone.

11. Can your tool break any stego image?
    No. Only images in our own formats. Shor runs only at toy size; larger keys get labelled estimates and never a time. Anything else is "unrecognised".

12. How does the analyzer decide which technique was used?
    Steganalysis features for the hiding method; blob length and structure for the cipher. It reports a confidence, the measured test-set accuracy (<value>), and "unrecognised" when nothing matches. RSA padding is "undetermined" because OAEP and textbook blocks look alike.

13. How do you know the analyzer's Shor stage is real?
    It calls the Q2 circuit builder with N read from the image. The static guard covers the module, and the change-the-question test uses two images carrying different N.

14. Why does the analyzer say "resists" for an ML-KEM image?
    Extraction works, but the layout shows nothing to factor, and AES-256-GCM is only Grover-weakened to about 128 bits. This is an inference from the layout, not a proof (any 1,088-byte string is a valid ML-KEM ciphertext, so only the secret key can confirm it).

15. What is the status of NIST IR 8547?
    Final since 27 October 2026. Quantum-vulnerable public-key algorithms are deprecated after 2030 and disallowed after 2035. Outside federal systems it is guidance.
