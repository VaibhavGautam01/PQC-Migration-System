# Commit Reference Check

Rule: every commit message references its GitHub issue, in the form
`type: description (refs #N)` or `(fixes #N)`.

Command used (merge commits excluded):

    git log --no-merges --format="%h %an | %s" | findstr /v "#"

## Known exceptions (before the convention was applied)

| Commit | Author | Message |
|---|---|---|
| fc0cb4b | Tarun Saxena | docs: redesign README with badges, pipeline diagram and tables |
| 84f7b2b | Tarun Saxena | docs: translate Hindi comments to English in scanner and extra_patterns |
| 624cb64, da07974, eb26b96, 43ea15d, 602d8af | Yatharth Raghuvanshi | "commit 1" to "commit 5" |
| 31121fd | Yatharth Raghuvanshi | "yatharth" |
| 3d85831, f12e2c4, f8fcea9, d4e7e39 | Yatharth Raghuvanshi | "Commit 1" to "Commit 4" |

These commits are kept as known exceptions. Pushed history was not rewritten,
because a force-push to main would break the other members' clones. All later
commits follow the convention.

## Limits of this check

- It finds commits with no issue number. It does not verify that the number
  given is the correct issue.
- It covers commits already on main. Re-run it after the final merge.
