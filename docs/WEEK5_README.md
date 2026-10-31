# Week 5 (Vaibhav) - commands, in order

Day-by-day mapping to the v3 6-week plan. Run everything from the project root, venv active.

## Day 1 - Q8 hardware + Analyzer test-set generator
```
python -m src.q8_check_access
python -m src.q8_hardware_run --dry-run
python -m src.q8_hardware_run --shots 128 --save      # only if q8_check_access shows real access

python extras/generate_test_set.py --count 1 --seed 1
python extras/generate_test_set.py --toy-n 15 21 35 221 --count 2
```

## Day 2 - rehearsal (no code)
Rehearse the attack demos and the evidence answers from docs/attack_evidence_master.md and
docs/viva_prep_vaibhav.md. Nothing to run here.

## Day 3 - final evidence check, Weeks 1 to 4
```
python -m src.evidence_gate --strict
python extras/evidence_check_weeks1to4.py
python extras/evidence_check_weeks1to4.py --json outputs/evidence_check.json
```

## Day 4 - viva Q&A update (done - see docs/viva_prep_vaibhav.md, now includes the v3
Stego Analyzer questions from Section 16)

## Day 5 - confirm Q8 access (same command as Day 1's first check)
```
python -m src.q8_check_access --json outputs/q8_access.json
```

## Tests
```
python -m unittest tests.test_generate_test_set tests.test_evidence_check -v
python -m unittest discover -s tests
```

## Commit
```
git add extras/generate_test_set.py src/q8_hardware_run.py src/q8_check_access.py extras/evidence_check_weeks1to4.py docs/viva_prep_vaibhav.md docs/WEEK5_README.md tests/test_generate_test_set.py tests/test_evidence_check.py
git status
git commit -m "feat: Week 5 - Q8 hardware run script, analyzer test-set generator, evidence check"
git push
```
