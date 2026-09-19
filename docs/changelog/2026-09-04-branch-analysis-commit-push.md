# 2026-09-04 — Branch analysis, commit and push of doc consolidation

## Requested

Analyze whether a new branch is the best approach for committing the
documentation version, then commit and push.

## Analysis result

No new branch. `refactor/rebuild` already exists for exactly this purpose
(the v2 rebuild), local tip matched the remote tip (53e5080) with no
upstream movement, and `main` holds the frozen v01 code — mixing contexts
there would be wrong. Committed on `refactor/rebuild` and pushed to its
upstream.

## Changed

- `refactor/rebuild`: commit `932aacd` — "docs: consolidate 26-file
  doc-set to 8 files; ADR-0006 case-file-first" (30 files, +673/−1466).
- Pushed: `origin/refactor/rebuild` now at `932aacd`. Working tree clean,
  branch in sync with upstream.

## Decisions

- Two-branch model kept: `main` = v01 reference (frozen);
  `refactor/rebuild` = v2 docs and future code.

## Left open

- Optional PR `main...refactor/rebuild` offered by the remote
  (http://10.110.193.143:4000/CFD/JAMAL/compare/main...refactor/rebuild)
  — not requested; owner decides.
