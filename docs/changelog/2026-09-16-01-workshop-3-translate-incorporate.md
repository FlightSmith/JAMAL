# 2026-09-16 — Workshop 20260916 translated and incorporated

## What was asked
Translate the new workshop record (`docs/workshops/20260916.md`) from
Portuguese and incorporate its decisions into the project documentation.

## What changed
- `docs/workshops/20260916.md` — translated to English in place
  (verbatim record; content unchanged, only language).
- `docs/SPECS.md` — §1 gained two subsections: **Transformation
  vectors** (references must exist in `geometry.transformation_vector`
  as `[point, direction]` pairs, fail-early check at load, hard-coded
  axis shortcuts `none`/`x`/`y`/`z`/`xy`/`xz`/`yz`/`xyz`, YAML example)
  and **Reference block** (`geometry.reference` with AIRCRAFT
  SREF/CREF/BREF/XREF/YREF/ZREF and PROPELER NBLADES/DIAM/CHORD/HUB/
  TILT). §1 Open extended with items 5–6 (vector syntax detail,
  reference-block schema). New **§8 Mesh generation workspace**:
  `./01-GRIDS` with `GEOM/`, `BATCH_SCENARIO/`, `GRIDS/` + lock against
  multi-user generation collisions.
- `docs/WORKSHOPS.md` — new outcome entry for Workshop 20260916
  (newest first) summarising the four promoted decisions.
- `docs/OPEN-QUESTIONS.md` — two new open questions: transformation-
  vector syntax (bare-name vs inline vector, `None` as point) and
  `geometry.reference` schema / overlap with the REF spec (§4).

## Decisions
- Workshop record translated in place (kept verbatim-record role per
  AGENTS.md; append-only folders untouched otherwise).
- Promotion path: spec edits only — no new ADR; the decisions refine
  SPECS §1 within ADR-0006's case-file-first model, and the mesh
  workspace is a layout proposal (Workshop status), not a shall.

## Open
- Transformation-vector syntax details (bare-name vs inline,
  `None`-as-point semantics) — SPECS §1 Open item 5.
- `geometry.reference` schema and its relationship to SPECS §4 (REF) —
  Open item 6; note source spelling "PROPELER" kept as-is.
- Mesh workspace: no spec yet on how the lock is implemented or who
  creates `01-GRIDS` (SPECS §8 status: Workshop).
