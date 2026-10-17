# Demo Recordings

Backup screen captures of the Shor's algorithm demos. The video files are
kept off GitHub (see .gitignore) and are stored locally and on a second
backup (pendrive / Google Drive).

| File | Case | Command | Result | Length | Date |
|---|---|---|---|---|---|
| shors_n15_demo_raw.mp4 | N = 15 (3 x 5), unedited | python notebook/shors_demo.py --case 15 | PASS | FILL_LENGTH | FILL_DATE |
| shors_n21_demo_raw.mp4 | N = 21 (3 x 7), unedited | python notebook/shors_demo.py --case 21 | PASS | FILL_LENGTH | FILL_DATE |
| shors_n15_demo_trimmed.mp4 | N = 15 (3 x 5), trimmed | python notebook/shors_demo.py --case 15 | PASS | FILL_LENGTH | FILL_DATE |
| shors_n21_demo_trimmed.mp4 | N = 21 (3 x 7), trimmed | python notebook/shors_demo.py --case 21 | PASS | FILL_LENGTH | FILL_DATE |

## How to regenerate

    venv\Scripts\activate
    python notebook/shors_demo.py --case 15
    python notebook/shors_demo.py --case 21

Both runs use the Aer simulator and need no internet connection.

## Editing notes

- Trimmed versions cut the command typing and the end of the run.
- FILL_SPEEDUP_NOTE (write "no section was sped up" if nothing was).
- The `_raw` files are the unedited originals.

Fallback instructions for the live demo: see `DEMO_FALLBACK.md`.
