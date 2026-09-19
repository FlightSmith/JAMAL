# 2026-09-10 — Workshop 2 definition updates

## What was asked
Translate the 2nd-workshop definition updates (from Portuguese) and
incorporate them into the appropriate docs.

## What changed
- `docs/workshops/20260910.md` — new verbatim record of the update
  (translated), the source for the edits below.
- `docs/SCOPE.md` — §5 UDF row corrected: UDF `.c` files are templates
  updated during the process to generate a `.c` with the correct values
  (was "UDFs are fixed `.c` files"). §6 spec table: REF and matrix are
  out of scope / no v2 workshop; flagged the open "what is `config`?"
  question.
- `docs/SPECS.md` — §1 required-sections draft: `geometry` expanded with
  `configuration`, `transformation_groups`, `infout_groups`;
  `control_surfaces` now has `transform`/`morphing` sub-sections with
  per-group operation lists. Transform/morph grammar section rewritten:
  `t_`/`m_` prefixes dropped (operations split into sections); fail-early
  rule added — transform group names must exist in `geometry` at load.
- `docs/OPEN-QUESTIONS.md` — grammar entry updated to the new model;
  added open question on the `config` spec.

## Decisions
- "config" resolved: it meant the site/tool configuration spec
  (`CONFIG-SPEC.md` pre-consolidation), now SPECS §5 — not the
  `geometry.configuration` case-file field. Question closed in
  OPEN-QUESTIONS.md; SCOPE §6 table now names specs by section number.

## Open
- Grammar details still open: reference kinds, units, ordering semantics.
