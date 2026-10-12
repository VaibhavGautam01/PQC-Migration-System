# Demo Recordings

Backup screen captures of the Shor's algorithm demos. The video files are
kept off GitHub (see .gitignore) and are stored locally by Yatharth.

| File | Case | Command | Result | Date |
|---|---|---|---|---|
| shors_n15_demo_raw.mp4 | N = 15 (3 x 5) | python shors_demo.py --case 15 | PASS | <date> |
| shors_n21_demo_raw.mp4 | N = 21 (3 x 7) | python shors_demo.py --case 21 | PASS | <date> |

## How to regenerate

    .venv\Scripts\activate
    python shors_demo.py --case 15
    python shors_demo.py --case 21

Both runs use the Aer simulator and need no internet connection.


| shors_n15_demo_trimmed.mp4 | N = 15 (3 x 5), trimmed | python shors_demo.py --case 15 | PASS | <length> | <date> |
| shors_n21_demo_trimmed.mp4 | N = 21 (3 x 7), trimmed | python shors_demo.py --case 21 | PASS | <length> | <date> |


## Editing notes

- Trimmed versions cut the command typing and the end of the run.
- <State here if any section was sped up, and by how much.>
- The `_raw` files are the unedited originals.

Fallback instructions for the live demo: see `DEMO_FALLBACK.md`.