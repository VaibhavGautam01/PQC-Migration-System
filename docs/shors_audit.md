Rule	Status	Finding
1 Real gates	Pass	Hadamards, controlled-U, inverse QFT, measurement, run on Aer
2 Result from measurement	Pass	Factors come from measured bitstrings. Fraction.limit_denominator and gcd are the allowed post-processing
3 No classical shortcut	Partial	N=15 uses hard-coded SWAP/X patterns in c_amod15, which bakes in the structure of the answer (the “compiled Shor” trap). N=21 builds the unitary from (m*x) % n, the allowed oracle. classical_period() brute-forces the period, but only for on-screen narration, so label it so
4 Evidence record	Fail	Nothing writes data/quantum_runs.json
5 Chi-square vs theory	Fail	Not done
6 Change the question	Partial	N=21 builder takes any coprime a. N=15 only supports a in {2,4,7,8,11,13}. N is a constant, not a parameter
7 Say what was simulated	Pass	“Aer simulator” is printed in step 4
8 Static guard test	Fail	No test scans the builders
9 Truth tables	Fail	Neither c_amod15 nor the permutation matrix is checked against Python arithmetic
10 Pin and seed	Fail	No seed_simulator or seed_transpiler, versions not recorded. APIs are current (transpile + AerSimulator.run)
11 Label	Partial	The label “Aer simulator, toy size” is not printed with the results

Your work follows from this table: Q1 (Vaibhav) replaces the N=15 shortcut with a generic builder, and your Q2 builds general gate-level modular arithmetic. File issues for the Fail rows using the real numbers GitHub gives them. I read the code in the zip, so please run these two commands to confirm the table before you commit it:
