# Q6 BB84 design (Aer simulator, toy size)

Status: DRAFT. Simulated protocol; real QKD needs dedicated optical hardware. ML-KEM stays the software-only recommendation.

## Protocol steps
1. Alice generates random bits and random bases (Z or X) and prepares one qubit per bit.
2. Bob picks random bases and measures.
3. Alice and Bob compare bases over the classical channel and keep matching positions (sifting).
4. They sacrifice a sample of the sifted key to estimate the error rate.
5. If the error rate is under the threshold, privacy amplification shortens the key to an AES-256 key. Otherwise abort.

## Eavesdropper test
- Intercept-resend by Eve should give an error rate near 25 percent on the sifted key.

## Threshold
- Abort threshold: ____ (confirm a source before choosing the number)

## Classical channel
- Authenticated with ML-DSA (messages signed so Eve cannot impersonate Alice or Bob).

## Open questions
- ____