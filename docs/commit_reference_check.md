\# Commit Reference Check



Rule: every commit message references its GitHub issue, in the form `type: description (refs #N)` or `(fixes #N)`.



Command used (run on origin/main, merge commits excluded):



&#x20;   git log origin/main --no-merges --format="%h %an | %s" | findstr /v "#"



Result as of this check: 12 commits on main carry no issue number.



| Commit | Author | Message |

|---|---|---|

| fc0cb4b | Tarun Saxena | docs: redesign README with badges, pipeline diagram and tables |

| 84f7b2b | Tarun Saxena | docs: translate Hindi comments to English in scanner and extra\_patterns |

| 624cb64, da07974, eb26b96, 43ea15d (and similar), 602d8af | Yatharth Raghuvanshi | "commit 1" to "commit 5" |

| 31121fd | Yatharth Raghuvanshi | "yatharth" |

| 3d85831, f12e2c4, f8fcea9, d4e7e39 | Yatharth Raghuvanshi | "Commit 1" to "Commit 4" |



These commits predate the commit-message convention being applied and are kept as known exceptions. Pushed history was not rewritten, because a force-push to main would break the other members' clones. All later commits follow the convention.



Limits of this check:

\- It finds commits with no issue number. It does not verify that the number given is the correct issue.

\- It covers commits already on main. Commits on feature branches appear after they are merged, so the check should be re-run after the final merge into main.

