# Sensitivity Analysis Plan (weights v0.1)

Owner: Yatharth Raghuvanshi. Script: `src/sensitivity.py` (Week 2 Day 1).
Output: `data/sensitivity_results.json` (generated; not committed unless the
team agrees). Quantum inputs are formulas and published estimates; no
simulator result is used.

## Question

The weights are our choice and are not fitted to data. How far do the scores
move if the weights are different, and does the **ranking** stay the same?

## What is varied

| Group | Parameters |
|---|---|
| Weights | the 3 quantum, 3 classical, 2 overall and 2 project weights in `data/risk_weights.json` |
| Assumptions | X = 2, 5, 10 years; Z = 5, 10, 20 years; Y = 2 (fixed) |

Thresholds (F3 bands, F4 values) are not varied in the first run. If time
allows, a second run varies the F4 and F6 values by 20 percent.

## Method

1. **One at a time.** Multiply one weight by 0.8 and by 1.2, re-scale its
   group to sum to 1, and re-score. Repeat for every weight.
2. **Random, narrow.** 1,000 draws. Each weight is multiplied by a uniform
   random number in [0.8, 1.2], then each group is re-scaled to sum to 1.
3. **Random, wide (stress test).** 1,000 draws. Each group is drawn from a
   uniform Dirichlet distribution, so any split of the group is possible.
4. **Assumption grid.** All 9 combinations of X and Z with the v0.1 weights.

Fixed seed (`seed = 42`) for all random draws, stored with the results.

## Cases scored

| Case | Used for |
|---|---|
| RSA-512 / RSA-1024 / RSA-2048+OAEP / ML-KEM-768 + AES-256-GCM | reference order |
| Image project, before and after migration | before/after ranking |
| Video project, before and after migration | before/after ranking |
| Image project vs video project (project score) | image vs video ranking |

The image and video project scores need Tarun's layer map (Week 2), so the
first run covers the four reference cases only.

## What is reported

- Min, max, mean and 5th to 95th percentile of each case's overall % and band.
- For each ranking, the fraction of draws in which it holds:
  - reference order (strict);
  - after < before for each project;
  - image vs video (whichever order v0.1 gives).
- Which single weight moves the score most (from step 1).
- The Z = 5, 10, 20 range beside the percentage, for the dashboard.

## Decision rule

A ranking is **stable** if it holds in at least 95 percent of the narrow
random draws and in every one-at-a-time case. If a ranking is unstable, the
cause is documented first, and a weight is changed only if the team agrees.
Every change gets a new version, a change-log entry in `docs/risk_model.md`
and a new lock (`python src/weights_lock.py write`). If all rankings are
stable, v0.1 becomes v1.0 in Week 2 Day 5 without changes.

## Expected difficulty

The image and video 1024-bit layers differ by only about 1 point in the
Day 4 review (80.9 vs 79.7). That ranking may flip under some weights. Test it;
do not assume either result.

## Limits to state in the report

- The weights are our choice. A narrow stable range shows the ranking is
  robust to our choices, not that the weights are correct.
- No ground truth exists for a probability, so nothing here validates the
  absolute percentage.
- X, Y and Z are assumptions agreed with sir (plan section 5).