# Codebase analysis & review progress — 2026-09-19

> **Status:** Working notes from the full read of docs + `JAMAL_shell` + `JAMAL_Struct_Folders`.
> Purpose: (1) track the review so it is not repeated from scratch, (2) collect weak
> points (documentation focus) with code references, (3) feed the rebuild plan.
> This file is a working document, not an ADR; findings get promoted via the
> normal process (workshop → ADR/spec edit).

## 1. What was read (complete)

| Area | Files | Depth |
|------|-------|-------|
| Docs | README, SCOPE, REQUIREMENTS, SPECS, DECISIONS, OPEN-QUESTIONS, WORKSHOPS, GLOSSARY, the frozen legacy analysis (now `workshops/20260918-requisitos-legacy-analysis.md`, incl. §14 source index), examples JSON README + polar-0002/0003 | Full |
| Hybrid Python | bin/jamal.py, app/core/simulation_case.py, app/core/workaround_to_shell.py, app/core/mesh_processor.py, etc/jamal.yml | Full |
| Legacy Bash | bin/jamal.sh (1893), lib/utils.sh (key fns: ISA, inversion, sweeps, journal emission, monitor, env_to_array), bin/posproc.sh (axes transforms + ADF writer) | Full flow; line-level on physics/sweep/ADF sections |
| Reference data | REF-001, SET-050, matrixpy, ansa_config_template.yaml, CARM.ansa.meshlog (label format) | Full |
| ANSA script | bin/ansamesh_script.py (4124) | Skimmed — retained unchanged per ADR-0007; only its YAML contract matters for v2 |

Not read line-by-line: class_Probes.py, class_postRakePoints.py, posproc optional
products (META/Flowvis) — parity-mode features, deferred per D06.

## 2. Understanding check — how JAMAL works today

Pipeline (matches REQUISITOS §3.1 flowchart, verified in code):

1. `jamal.py` parses matrix text → validates via COLUMN_CONFIG pipeline
   (validators → transformers → post-validators) → `SimulationCase` (pydantic).
2. `MeshProcessor` (only when GRID is `run_ansa_batch*`/YAML): builds config
   name from geometry/*t/*m/controls sections, substitutes into
   `ansa_config.yaml` (zero-fill to MAX_GEOM=5, MAX_TRANS=12, MAX_MORPH=12),
   runs `ansa64.sh` via LMOD, validates by **scraping meshlog patterns**.
3. `workaround_to_shell.py` flattens case → env vars (`*_ARRAY` JSON lists) →
   runs `jamal.sh`.
4. `jamal.sh`: mesh-name rebuild (duplicates Python logic), meshlog regex
   validation, SET/REF loading (line 471–604), run dir + symlinks (incl.
   start-from-polar-case), ISA physics (utils.sh 349–510), zone/PID parsing
   from meshlog (jamal.sh 1146–1280), sweep planner (1449–1768: 4+ nested
   branch cases), journal emission via SET substitution + `set_flow_cond_sequence`,
   UDF `coef_driver.c` population (CLS/CYS modes), `to_run.sh` with
   `submit_fluent` calls, transcript monitoring → `posproc.sh`.
5. `posproc.sh`: reads `infout` + FORCE/MOMENT reports → wind↔body↔CFD axis
   transforms → ADF (32 metadata fields, 22 columns — verified lines 659–688).

Key legacy behaviours confirmed in code (backing the docs' claims):

- `pressure()` hardcodes ISAD=0 (utils.sh ~433) while T/ρ/μ take ISAD → the
  R-01/R-02 pattern; **but** D01 correctly notes the shell is "pressure
  altitude" oriented, so this is a *convention conflict*, not simply a bug.
- Reynolds inversion: Newton on T, inlined S=110.4 and μ_ref=1.458e-6,
  tolerance = |ΔRe| < 1 (absolute), **no iteration cap** (utils.sh 349–410,
  loop at 994–1018).
- KNITERS `3:0.1:1` → first point 3000 iters, others 1000; middle element
  only feeds UDF driver ratios via SET (0.1/0.15/0.4/1.0).
- Alpha sweep -10…20: 0 → +1…+20 → reload saved 0 (`read_case_data_jou`)
  → -1…-10, one journal/SET, one Fluent session. Matches ADR-0008/FR-030.
- POLAR 003 pattern: `GRID: POLAR-...` branch symlinks cas/dat/FORCE/MOMENT
  from source polar; first point emitted with `0000` iters (reused, no
  re-solve). Matches ADR-0008 amendment/FR-033.
- Matrix is mutated during submission (`sed -i "$line_number s/^…/0/"`,
  jamal.sh 1874) — input used as state (RP-IN-05 violation, correctly banned).

## 3. Weak points found

> **Resolution note (2026-09-19):** every DOC-* item below was auto-fixed
> or resolved by owner decision in the same session — see §5 Progress log.
> Items are kept for the record; fix directions were applied as stated.

### Documentation (focus)

| ID | Weakness | Impact | Fix direction |
|----|----------|--------|---------------|
| DOC-01 | Broken internal links: REQUISITOS §14 and 6 other files link to `C:/Users/User/Documents/ChatGPT/JAMAL 2/...` (Windows/ChatGPT-export paths). | Every link is dead for all developers on the git repo. | Rewire to relative repo paths (`../JAMAL_shell/...`). |
| DOC-02 | `docs/README.md` "History"/"Legacy note" reference branch `refactor/rebuild`, commit 53e5080, and "v01 code on main (app/, bin/, tests/)" — none true after the clean-slate import; `JAMAL_shell/tests/` doesn't exist in the delivered package (S13 references `tests/integration/test_cases.py` — absent). | New developers can't reconcile history; S13's source is missing. | Rewrite History section for this repo; note missing tests fixtures. |
| DOC-03 | `docs/README.md` and WORKSHOPS reference `AGENTS.md` ("see AGENTS.md") and `jamal_matrix.jpeg` — neither exists in the repo. | Process rules for workshops/changelog are dangling. | Add AGENTS.md (multi-dev conventions) or drop references; import matrix image. |
| DOC-04 | D01 (altitude/ISA semantics) is marked a review hold on SPECS §2, yet SPECS §2.2–2.7 read as normative and REQUIREMENTS FR-012/013 already prescribe geometric altitude + ISAD-in-hydrostatic. Three positions coexist: legacy (pressure-altitude, p at ISAD=0), SPECS draft (geometric, ISAD in p), D01 (undecided). | First physics module cannot start without an owner decision; tests can't have golden values. | Dedicated decision workshop (W-physics) before FR-012 implementation; document the rejected alternative. |
| DOC-05 | D02 contradiction stated but unresolved in three places (SPECS §3, OPEN-QUESTIONS, REQUISITOS §8): mesh metadata producer. FR-016/019 + WONT-004 forbid log scraping; ADR-0007 keeps ANSA script unchanged; the only artefact the script makes is the meshlog (which MeshProcessor and jamal.sh both scrape today). | FR-016 acceptance is untestable as written. | Decide: external structured collector vs bounded transitional exception in the ANSA adapter; amend FR/WONT accordingly. |
| DOC-06 | ID spaces are one-directional: REQUISITOS RP-* maps to FR-* in prose, but REQUIREMENTS never references RP-*; FR-028/029 are physically listed after FR-033 (ordering broken). | Traceability requires reading both docs side-by-side. | Add a mapping table (RP ↔ FR/QA/OP) and renumber or index FR-028/029. |
| DOC-07 | SPECS §1 "Required sections" are YAML sketches while ADR-0006/0007 made JSON the interface; examples exist (`polar-0002/0003.json`) but SPECS doesn't reference them. | Two notations for the same contract invite drift before W1 even freezes the schema. | Point SPECS §1 at the JSON examples as the notation of record. |
| DOC-08 | SET-050 vs SET-055 (density- vs pressure-based families) documented as needing "named numeric recipes" (RP-SO-02), but the JSON draft ships exactly one profile (`density_based_implicit_steady_v1`) and SPECS §6 leaves the recipe catalogue open. | AC-09 can't be written; parity gap discovered late. | W3 deliverable: enumerate the recipe set required for parity, sourced from SET-050/055 diff. |
| DOC-09 | Sweep policy table missing: ADR-0008 confirms only zero-crossing alpha (and 003 beta); the legacy code has 6+ branch shapes (one-sided alpha/beta, beta zero-crossing, aoa_grid, multi-mesh, COLD per-point journals). D03 defers them, but docs don't inventory *what* the legacy shapes are, so "parity" has no checklist. | Scope creep or silent feature loss at parity time. | Add a legacy-behaviour inventory (from jamal.sh 1449–1768) to OPEN-QUESTIONS/D03. |
| DOC-10 | No contributor workflow for a multi-dev repo: no AGENTS.md/CONTRIBUTING, no ADR "how to propose" beyond prose, changelog conventions only referenced, never specified. | Partner onboarding is tribal knowledge. | Minimal CONTRIBUTING + ADR template; decide PR vs direct-push policy. |

### Code observations worth carrying into the rebuild (not compatibility goals)

- `jamal.sh:427` — `$multi_mesh_filesi` typo (undefined var) in the
  existing-mesh validation guard; that validation silently never runs.
- `mesh_processor.py:_check_neg_vol_section` — `raise` followed by dead
  `return True`; inconclusive neg-vol is logged at DEBUG and treated as OK
  ("assuming ok") — exactly what RP-ME-06/AC-08 forbid for the new system.
- `validators.validate_positive_integer` accepts 0 (`v == abs(v)`); RUN/POL
  of 0 would pass (matrix RUN=0 lines are skipped earlier by luck of the
  parser, not by validation).
- `SimulationCase.define_probes` crashes on `PROBES=None`.
- Physics loops (`while true`) in shell have no iteration caps; new system
  already requires them (FR-014) — keep the requirement, note the legacy
  behaviour as classification-only.
- Units: `ansa_config_template.yaml` mixes mm geometry and m reference
  lengths field-by-field (confirms REQUISITOS §8; adapt per-field, never a
  global scale).
- meshlog labels: producer writes `Fluid PIDs:`; consumers grep `Fluid: `
  (jamal.sh 1155) — normalization must be versioned (REQUISITOS §8 row 6).
- `submit_fluent` is not in the package (external site script) — D07 stands.

## 4. Rebuild plan — inputs now in hand

Everything W1 needs is identified; the blocking decisions are D01, D02, D03
(partially), D05. Sequence aligned with REQUISITOS §12.2 and docs README:

1. Resolve DOC-04/05 (D01/D02) with the owner — small, decisive workshops.
2. W1 case-file schema (JSON of record = examples + SPECS §1 fields).
3. Pure core: physics module (DC-007 single constants source), planner
   (RP-SW-01 explicit plan artifact), name/key builders.
4. Journal builder + injection/suppression (W3), UDF template population.
5. ANSA adapter (YAML contract from template; isolation + content-key cache).
6. PBS adapter, state/resume, orchestrator.
7. Postprocessor (ADF contract per SPECS §9; golden ADF from owner for D05).

## 5. Progress log

- [x] Repo import fixed: JAMAL_shell vendored (embedded gitlink + credentialed
      URL removed from history; **token rotation on internal GitLab still owed
      by owner**), single-commit initial state pushed (3130749).
- [x] Full docs read; full hybrid-code read (per table §1).
- [x] Weak points collected (§3).
- [x] Understanding summary delivered to owner (2026-09-19).
- [x] Owner decisions received (2026-09-19): ADR-0009 (D01 closed, geometric
      altitude + ISAD everywhere), ADR-0010 (D02 closed — isolated meshlog
      parser, swappable), ADR-0011 (numerics profiles from SET-050/055),
      ADR-0012 (legacy sweep semantics as parity baseline), YAML/JSON
      interchangeable input.
- [x] DOC-01 fixed: all ChatGPT-export links rewritten; zero broken links
      (verified by link check over docs/**/*.md).
- [x] DOC-02 fixed: README History rewritten for this repo; missing legacy
      tests noted as removed deliberately (recoverable from delivery archive).
- [x] DOC-03 fixed: AGENTS.md references replaced by CONTRIBUTING.md;
      jamal_matrix.jpeg references replaced by `matrixpy`.
- [x] DOC-04/05 resolved via ADR-0009/0010; SPECS §2 promoted to normative;
      OPEN-QUESTIONS updated.
- [x] DOC-06 fixed: docs/TRACEABILITY.md (RP↔FR map + FR-028/029 ordering note).
- [x] DOC-07 fixed: SPECS §1 names the JSON examples as notation of record;
      YAML/JSON interchange stated.
- [x] DOC-08 fixed: ADR-0011 profile catalogue seeded from SET-050/055 diff;
      examples updated to `fluent_density_based_v1` + `solver_family`.
- [x] DOC-09 fixed: docs/LEGACY-SWEEP-INVENTORY.md (12 shapes + deliberate
      non-reproductions).
- [x] DOC-10 fixed: docs/CONTRIBUTING.md + docs/templates/ADR.md.
- [ ] Owner review of this batch.
- [ ] W1 case-file schema workshop (next).
