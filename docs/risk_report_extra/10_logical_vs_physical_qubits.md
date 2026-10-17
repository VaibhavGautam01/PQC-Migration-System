## Logical vs Physical Qubits: Why These Numbers Are Not Breakable Today

The qubit counts in this report (for example 4,099 for a 2048-bit RSA key)
are **logical qubits**. A logical qubit is an ideal, error-free qubit. Real
quantum hardware is built from **physical qubits**, which are noisy: every
gate and every moment of idle time has a chance of flipping a value. Shor's
algorithm runs billions of gate operations, so it cannot succeed on raw
physical qubits.

### Error correction and its overhead

Quantum error correction fixes this by spreading one logical qubit across
many physical qubits. With the surface code, the leading approach, the
overhead depends on the physical error rate and on how long the computation
runs. Typical estimates are hundreds to thousands of physical qubits for
each logical qubit.

### What this means for the results

| Project | RSA modulus | Logical qubits (2n+3) | Physical qubits at 1,000:1 (illustrative) |
|---|---|---|---|
| Secure-Video-Steganography | 2048 bits | 4,099 | about 4.10 million |
| Final-Year-project-part1 | 256 bits | 515 | about 515 thousand |
| Final-Year-project-part1 | 8 bits | 19 | about 19 thousand |

The 1,000:1 ratio is an **assumption chosen for illustration**, not a
measured value. The real ratio depends on future hardware quality.

### Why this is not breakable today

- The largest quantum processors built so far have on the order of a
  thousand physical qubits, with error rates too high for deep circuits.
- Published resource estimates for RSA-2048 (for example Gidney and Ekera,
  2019) need millions of physical qubits, with later work lowering the
  figure. Those papers use optimized circuits whose logical-qubit counts
  differ from the 2n+3 formula used here.
- The logical count in this report is therefore a **lower bound on
  difficulty**, useful for comparing keys and tracking progress, not a
  prediction of when an attack becomes possible.

### Why migrate anyway

Data encrypted today can be recorded now and decrypted later
("harvest now, decrypt later"). Migration takes years, so the
recommendation in this report does not wait for the hardware.

### Important exception: toy key sizes

The 8-bit and 256-bit RSA moduli in Final-Year-project-part1 are breakable
on an ordinary computer today. They are a **classical** weakness, covered
by the key-strength check, not a quantum one.