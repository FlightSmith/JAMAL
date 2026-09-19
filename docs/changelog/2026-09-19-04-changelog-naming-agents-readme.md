# 2026-09-19-04 — Changelog naming, reviews/ folder, AGENTS.md, root README

Changelog entries renamed to `YYYY-MM-DD-NN-slug.md` (two-digit sequence
per day) to disambiguate multiple same-day entries; the convention is now
specified in AGENTS.md §4 and docs/README.md.

`docs/ANALYSIS-2026-09-19.md` moved to
`docs/reviews/2026-09-19-codebase-analysis.md` (dated analyses get their
own folder; docs root stays living-docs only).

New `AGENTS.md` at repo root: operating guide for AI agents/harnesses —
repository map, mandatory reading order, document precedence, change
procedures (ADR process, changelog naming), hard prohibitions (frozen
trees, append-only folders, no ID renumbering), commit conventions, and
verification checklist.

New root `README.md`: project front door for humans — status, doc
reading order, pointer to AGENTS.md for agents.

Touches: docs/changelog/* (renames), docs/reviews/ (new), AGENTS.md,
README.md, docs/README.md.
