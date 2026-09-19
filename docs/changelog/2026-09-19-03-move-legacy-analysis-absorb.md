# 2026-09-19 — Move legacy analysis to workshops/, absorb its living content

`REQUISITOS-REFACTOR-PYTHON.md` moved to
`workshops/20260918-requisitos-legacy-analysis.md` (git mv, history
follows) and marked as a FROZEN ANALYSIS RECORD superseded by
DECISIONS/REQUIREMENTS/SPECS/OPEN-QUESTIONS/TRACEABILITY. Closure notes
for D01/D02/D03 added at the top; original text verbatim.

Absorbed into living docs:
- AC-01…20 → new `docs/ACCEPTANCE-SCENARIOS.md` (English, living; stale
  D01/D02 blockers annotated with their ADRs).
- D04–D08 → `docs/OPEN-QUESTIONS.md` new section, incl. the D05 external
  team sign-off requirement and D08 dummy-input replacement list.
- §9 legacy ADF format (22 columns / 32 metadata fields, normalization
  relations, axis-convention warnings) → `docs/SPECS.md` §9.1, with the
  external-team contract note.
- §8 ANSA limits table → `docs/SPECS.md` §8.1, extended with the owner's
  planned `ansamesh_script.py` rewrite (arbitrary geoms/params, structured
  named input, per-field units, structured metadata output replacing the
  meshlog parser).

All inbound/outbound links rewired; link checker clean.

Touches: docs root files, docs/workshops/*, docs/SPECS.md,
docs/OPEN-QUESTIONS.md, docs/README.md, docs/TRACEABILITY.md.
