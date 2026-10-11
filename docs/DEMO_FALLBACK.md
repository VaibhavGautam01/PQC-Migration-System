# Live Demo Fallback Plan

Owner: Yatharth Raghuvanshi

## Before the presentation (15 minutes early)

- [ ] Laptop plugged in; power mode set to best performance
- [ ] Notifications off; unrelated windows closed
- [ ] Terminal font enlarged; `(.venv)` visible in the prompt
- [ ] Dry run: `python shors_demo.py --case 15` prints `[PASS]`
- [ ] Trimmed videos open and play from the local `recordings\` folder
- [ ] Same videos open from the second backup location
- [ ] Slides or the demo window ready on the projector or screen share

## Live command

    .venv\Scripts\activate
    python shors_demo.py --pause

Press Enter between steps. Explain each step while the screen waits.

## If something goes wrong

| Problem | What to do |
|---|---|
| Run is too slow (N = 21) | Stop with Ctrl+C, then run `python shors_demo.py --case 21 --shots 256`, or play the N = 21 video |
| `[FAIL]` or an error appears | Do not debug live. Say "let me show the recorded run", then play the trimmed video |
| Environment or import error | Same: play the trimmed video |
| Laptop or projector fails | Use the copy on the second backup device, or a teammate's laptop |
| Nothing works | Walk through the printed output saved in the report and slides |

## Be honest about what the audience sees

- Say clearly when you switch to a recording: "this is a recorded run of the same program."
- Shor's is probabilistic. A run where some outcomes show "none (unlucky)" is normal and worth explaining, not hiding.
- State that the qubit counts for real RSA keys are logical qubits, and that the demo uses toy numbers.

## Files

| File | Where |
|---|---|
| shors_n15_demo_trimmed.mp4 | local `recordings\` + second backup (not in Git) |
| shors_n21_demo_trimmed.mp4 | local `recordings\` + second backup (not in Git) |
| Log and fingerprints | `RECORDINGS.md` |

## Contacts

If Yatharth's laptop fails, Tarun or Uday can run the demo from `main`:

    git checkout main
    git pull origin main
    pip install qiskit qiskit-aer numpy
    python shors_demo.py --pause