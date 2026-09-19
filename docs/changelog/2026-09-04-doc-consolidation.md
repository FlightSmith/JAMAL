# 2026-09-04 — Documentation consolidation + branch switch

## Requested

1. Analyze all docs (on `main`) for inconsistencies, coherence, simplicity;
   plan changes in phases.
2. Decision taken by owner: JSON/YAML case-file-first model (one
   self-contained file per simulation; matrix becomes a future
   generation/derivation layer).
3. Consolidate the 26-file doc-set to ~6 files.
4. Correction: work should happen on `refactor/rebuild` (where the doc-set
   and workshop 20260902 live). Consolidate again on that branch.
5. Keep `docs/workshops/` (meeting/idea records) and add
   `docs/changelog/` (summary per request); write AGENTS.md so agents know
   to update both.

## Changed

- `docs/DECISIONS.md` — new: ADR-0001…0005 compressed; **ADR-0006**
  case-file-first accepted; ADR-0005 struck through (superseded);
  restart-wishlist + matrix layer parked.
- `docs/SPECS.md` — new: §1 case file (first implementation target), §2
  equations (near-frozen), §3 mesh metadata, §4 REF, §5 config, §6 solver
  input + injection/suppression, §7 future matrix layer.
- `docs/REQUIREMENTS.md` — rewritten: 83 → ~54 shalls; FR-001…011 for the
  case-file model; matrix shalls removed (WONT-007); WISHLIST section.
- `docs/SCOPE.md` — updated for case-file-first; matrix out of scope v2.
- `docs/WORKSHOPS.md` — workshop 20260902 outcome recorded and promoted
  (ADR-0006, ADR-0003 amendment); W1 rewritten as case-file schema agenda.
- `docs/OPEN-QUESTIONS.md` — re-anchored on case-file model; v01-pain
  table folded in.
- `docs/GLOSSARY.md` — updated for case-file vocabulary.
- `docs/README.md` — rewritten as 8-file map + rules + history pointer.
- `AGENTS.md` — new: mandatory workshops/ and changelog/ folders.
- `docs/workshops/20260902.md` — restored (meeting record, verbatim).
- Deleted (full text in git history, commit 53e5080): `MANIFEST.md`,
  `architecture/` (ARCHITECTURE + 5 ADRs), `engineering/`,
  `operations/`, `rationale/`, `specs/` (7 files), `workshops/W1–W3`.

## Decisions

- ADR-0006 supersedes ADR-0005 (workshop 20260902 + owner confirmation).
- v01 code on `main` frozen as reference; v2 starts clean on
  `refactor/rebuild` after W1 accepts the case-file schema.
- Glossary kept (unlike MANIFEST) as shared domain vocabulary.

## Left open

- W1 workshop: exact case-file schema (first implementation target).
- Results schema for post-process (FR-028 → TBD).
- Solver restart α/β: parked in wishlist.
- Commit not made — awaiting owner review.
