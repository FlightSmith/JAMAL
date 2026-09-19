# JAMAL v2 — Requirements

> **Status:** Draft shalls. Syntax of inputs is defined in `SPECS.md`, not here.
> Every requirement: **ID, Priority (Must/Should), Statement, Spec, Verify**.
> Backend boundary and sweep behaviour updated by ADR-0007/0008. Atmosphere
> semantics fixed by ADR-0009; mesh-metadata producer by ADR-0010; numerics
> profiles by ADR-0011; sweep parity baseline by ADR-0012.

> **Legacy-analysis review (2026-09-18):** the new
> [Python refactor requirements](<workshops/20260918-requisitos-legacy-analysis.md>)
> expand coverage from the supplied implementation. Its D01/D02 identified
> the atmosphere and metadata conflicts — both now closed by ADR-0009 and
> ADR-0010. D03 direction is set by ADR-0012 (legacy sweep semantics).

---

## FR — Functional

### Case file (ADR-0006 model, amended by ADR-0007)

| ID | Pri | Statement | Spec | Verify |
|----|-----|-----------|------|--------|
| FR-001 | Must | The backend shall parse a JSON case file holding the engineering data and artefact references needed for one simulation, without requiring matrix or REF input files. | SPECS §1, ADR-0007 | JSON fixture parses without matrix/REF; unknown major version → hard fail |
| FR-002 | Must | The system shall validate each field against a schema and run cross-field checks after parsing. | SPECS §1 | Invalid enum / arity / missing reference quantity → named error |
| FR-003 | Must | The system shall reject duplicate case identities within a campaign run. | SPECS §1 | Duplicate POL (+suffix) → error naming both |
| FR-004 | Must | The system shall accept scientific notation in numeric fields. | SPECS §1 | `24e6` = 2.4×10⁷ |
| FR-005 | Must | The system shall fail on schema or field-shape mismatches with file path and field location. It shall not guess. | SPECS §1 | Truncated file → hard fail |
| FR-006 | Must | The system shall enforce sweep exclusivity: at most one of α / β / Mach (or coefficient/velocity modes) is a multi-value sweep per case. | SPECS §1 | Two sweeps → error |
| FR-007 | Must | The system shall reject incompatible specification modes (in particular velocity **and** Reynolds-from-altitude). | SPECS §2 | VEL+REY → error |
| FR-008 | Must | The system shall validate surface/propulsion arities and named references against the definitions supplied in the JSON case; mismatch → error. | SPECS §1 | Wrong rudder arity or missing hinge definition → error |
| FR-009 | Must | The system shall support transform/morph operations on geometry per the grammar frozen in SPECS §1. | SPECS §1 | Same inputs → same mesh config name |
| FR-010 | Must | The system shall resolve morphing mode deterministically from case parameters: none, morph-only, control-surfaces-only, both. | SPECS §1 | Mode derived from case file |
| FR-011 | Must | The system shall skip explicitly disabled cases without treating them as errors. | SPECS §1 | Disabled case absent from the run set; matrix comments are outside the backend |

### Atmosphere and flow

| ID | Pri | Statement | Spec | Verify |
|----|-----|-----------|------|--------|
| FR-012 | Must | The system shall compute T, p, ρ, μ, and speed of sound from geometric altitude and ISA deviation for 0–20 km. | SPECS §2 | Golden values; layer switch at 11 km; ISAD ≠ 0 |
| FR-013 | Must | Pressure and temperature used for density shall be evaluated at the **same** ISA deviation. | SPECS §2 | ISAD≠0: ρ ≠ mix of p(ISAD=0) and T(ISAD) |
| FR-014 | Must | The system shall invert Mach, Reynolds number, reference length, and ISA deviation to geometric altitude in [0, 20] km, with a closure check (relative Re error < 1e-6) that fails on violation. | SPECS §2 | Newton + bounds; forced non-convergence → error |
| FR-015 | Must | The system shall convert between Mach and velocity using the speed of sound at the resolved conditions. | SPECS §2 | Round-trip |

### Mesh

| ID | Pri | Statement | Spec | Verify |
|----|-----|-----------|------|--------|
| FR-016 | Must | The system shall obtain a volume mesh for a case or reuse a mesh **proven valid** for that case's geometry and mesh parameters. | SPECS §3, ADR-0001, ADR-0010 | Missing/invalid metadata → case fails; no log scraping in domain code (isolated parser adapter allowed per ADR-0010) |
| FR-017 | Must | Cases sharing geometry and mesh parameters shall share **one** mesh artefact, referenced by symlink. | ADR-0001 | Two flow conditions, one mesh inode |
| FR-018 | Must | When mesh generation is required, the backend shall adapt JSON meshing parameters and geometry references to the existing YAML interface and invoke the current ANSA script with LMOD; that script continues to handle transformations and morphing. | SPECS §8, ADR-0007 | YAML reflects JSON inputs; existing ANSA script invoked; module load isolated |
| FR-019 | Must | Mesh success shall be decided only from the mesh-metadata contract (SPECS §3) plus `mesh_path` existence. In the current phase the metadata is produced by the isolated meshlog-parser adapter (ADR-0010); domain code never reads the log. | SPECS §3, ADR-0010 | Raw `.log` consumed outside the parser adapter → hard fail |
| FR-020 | Must | The system shall build a deterministic, human-readable mesh configuration name from case parameters. | SPECS §1 | Same inputs → same name |

### Solver input

| ID | Pri | Statement | Spec | Verify |
|----|-----|-----------|------|--------|
| FR-021 | Must | The system shall emit a complete, valid Fluent journal for each case, from the numerics profile named in the case file (ADR-0011 catalogue); leftover unsubstituted placeholders are a hard failure. | SPECS §6, ADR-0011 | Token audit; golden excerpts for both seeded profiles |
| FR-022 | Must | The journal shall execute the operating points of a sweep in one Fluent session, continuing from the current solution within each branch and updating the applicable flow conditions between points. | SPECS §6 | One session; alpha/beta changes update far-field direction without reinitializing within a branch |
| FR-023 | Must | The operator shall be able to **inject** extra solver input (snippets at hook points, overrides, extra files) and **suppress** generated commands. Injection is explicit and versioned with the case. | ADR-0003 + amendment, SPECS §6 | Injected block appears; suppression removes target; missing path → fail screaming |
| FR-024 | Must | For active CL-driver, CY-driver or MFR modes, the backend shall populate existing UDF `.c` templates with case-specific values in the isolated case workspace and emit the required compilation/loading hooks. No UDF generation or compile hook is required when these modes are inactive. | SPECS §6, ADR-0007 | Values match the case; no unresolved placeholders; shared templates unchanged; hooks match active mode |
| FR-025 | Must | If a symmetry boundary exists (named in configuration/mesh metadata), the reference area used for coefficients shall be halved. | SPECS §3 | Sref_used = Sref/2 |
| FR-026 | Must | The system shall support fan inlet (mass-flow), fan outlet, and core-exhaust BC groups with arities validated against the definitions supplied in JSON. | SPECS §1, §6 | Group arity validated |
| FR-027 | Must | Fluent material viscosity shall be generated from the same Sutherland constants as the ISA module. | SPECS §2, DC-007 | Constants equal in journal and module |
| FR-030 | Must | For alpha sweeps spanning zero, the journal shall solve and save the point closest to zero, execute the branch away from zero, reload the saved near-zero solution, then execute the opposite branch away from it, within the same Fluent session (ADR-0012 legacy semantics; the confirmed -10…+20 example is a special case). | SPECS §6.1, ADR-0008, ADR-0012 | -10 to +20 by 1 executes 0, +1…+20, reload 0, -1…-10; zero is not solved again at the reload |
| FR-031 | Must | Each computed operating point shall run its full specified iteration count. Solver convergence checks shall neither advance a point early nor gate the remaining sweep in the current phase. A reused first point follows FR-033. | SPECS §6.1, ADR-0008 | Each computed point emits its requested iteration count; no convergence-based branch or early stop |
| FR-032 | Must | The backend shall support starting a polar from another polar's saved operating-point mesh and solution, waiting for that source point to become available without requiring the whole source polar to finish. | SPECS §6.2, ADR-0008 | POLAR 003 waits for POLAR 002 alpha 0, loads its saved solution, and does not generate a new grid |
| FR-033 | Must | A first point supplied by another polar's saved solution shall be reused without new iterations, retaining its results and source provenance. | SPECS §6.2, ADR-0008 amendment | POLAR 003 reuses beta 0 and calculates beta 1…15: 16 result points, 15 newly computed |

### Post-process

| ID | Pri | Statement | Spec | Verify |
|----|-----|-----------|------|--------|
| FR-028 | Must | The backend shall invoke a dedicated post-processing script to produce an ADF containing three force and three moment coefficients in each of the body, wind and stability axes. Flow figures, Cp and load distributions shall be optional outputs. | SPECS §9, ADR-0007 | Representative solver outputs produce the agreed ADF; ADF production does not require optional figures/distributions |
| FR-029 | Should | Probe-point and rake-point diagnostics declared in the case file shall be supported. | SPECS §1, §6 | Probes in journal iff declared |

---

## IF — Interface

| ID | Pri | Statement | Spec |
|----|-----|-----------|------|
| IF-001 | Must | JSON case files at the frontend/backend boundary shall conform to SPECS §1. | ADR-0007 |
| IF-002 | Must | Engineering definitions previously obtained from REF shall be supplied through the JSON interface and validated under SPECS §1. A separate REF file shall not be required by the backend. | ADR-0007 |
| IF-003 | Must | Mesh metadata shall conform to SPECS §3; unknown major version → hard fail. | draft 1.0 |
| IF-004 | Must | Generated journals and injection artefacts shall conform to SPECS §6 once accepted. | W3 |
| IF-005 | Must | Site/tool configuration shall conform to SPECS §5; validated at startup. | W-config |
| IF-006 | Must | Each domain package shall export/import its data as JSON or YAML. | ES-012 |
| IF-007 | Must | Campaign/run state shall be a structured file. | ADR-0002 |

---

## QA — Quality

| ID | Pri | Statement | Verify |
|----|-----|-----------|--------|
| QA-001 | Must | **Fail screaming.** Invalid input, missing file, schema-invalid artefact, or failed external tool → immediate, descriptive error. No partial silent output, no guessing, no leftover placeholders. | Negative tests per failure class |
| QA-002 | Must | **Run isolation.** Overlapping invocations shall not write the same mutable path. Shared meshes: write-once, read-only after. | Two processes, distinct work roots; cache lock test |
| QA-003 | Must | External invocations mutating `PATH` or loading LMOD shall restore the environment on completion **and** failure. | Env diff empty after ANSA/Fluent |
| QA-004 | Must | Same inputs → same outputs. Generated names and journals shall not embed wall-clock time unless a documented timestamp field is part of the contract. | Bit-stable journals in tests |
| QA-005 | Must | Structured logging with case id, stage, status, timestamp, message. | JSON-lines or parseable log |
| QA-006 | Must | End-of-run summary: N succeeded, failed, skipped, with reasons. Always printed, including all-fail. | Summary in every run |
| QA-007 | Must | Portable on PBS + LMOD Linux; tool versions and paths from configuration. | No hardcoded site path in domain |
| QA-008 | Must | Mesh generation is idempotent within sharing rules: a valid cached mesh is not rebuilt. | Second run: zero ANSA |
| QA-009 | Must | Observability: an operator can answer "what happened to case 17?" without grepping unstructured blobs. | Per-case stage in state + logs |
| QA-010 | Should | Tool versions and a content hash of the active configuration recorded in each case record and state file. | Present after a run |

---

## OP — Operational

| ID | Pri | Statement | Notes |
|----|-----|-----------|-------|
| OP-001 | Must | Three execution modes: **0** prepare files only; **1** submit; **2** submit + monitor + post-process. Later stages skipped or no-op, not deleted. | — |
| OP-002 | Must | Per-case run flag: skip / run / force re-run; force re-run has a defined artefact-invalidation effect. | Open: what force deletes |
| OP-003 | Must | Each invocation has a unique **work root**; mutable artefacts live under it. | ADR-0001 |
| OP-004 | Must | **Resume** from the last successful stage per case, using both state file and artefact presence/validity; conflict → fail screaming or documented reconcile. | ADR-0002 |
| OP-005 | Must | Job submission to PBS with configured walltime, CPU count, and modules. | Mode 1/2 |
| OP-006 | Should | `--fail-fast` stops the batch on first case failure; default continues and still prints the QA-006 summary. | — |

---

## UX — Operator experience

| ID | Pri | Statement |
|----|-----|-----------|
| UX-001 | Must | Numeric fields may carry a unit suffix (`_m`, `_ft`, later `_m/s`, `_kts`); unsuffixed values use a declared default; internal SI. |
| UX-002 | Must | Case identity (POL) is a 4-digit base `0000`–`9999` plus optional alphanumeric suffix; unique per campaign. |
| UX-003 | Must | The case file is comprehensible to a human: domain names, not only solver tokens. |
| UX-004 | Must | Concurrent campaigns/runs are a supported workflow. |
| UX-005 | Could | Installable CLI (`jamal …`) vs `python -m jamal`. |

---

## DC — Design constraints

| ID | Pri | Statement |
|----|-----|-----------|
| DC-001 | Must | SI internally; convert at the I/O boundary. |
| DC-002 | Must | Domain modules shall not import ANSA, Fluent, PBS, or LMOD adapters. |
| DC-003 | Must | Solver access through a port. Fluent is the v2 implementation; SU2 addable next year without changing case, ISA, or parsing code. SU2 behaviour Won't v2. |
| DC-004 | Must | No site-specific paths, module names, or tool versions in code. |
| DC-005 | Must | Validation rules, tool versions, quality thresholds are configuration-driven. |
| DC-006 | Must | Physics, validation, name-building, and substitution planning have no filesystem, environment, or subprocess access (pure core, impure edge). |
| DC-007 | Must | One module is the single source of truth for γ, R, g, ISA constants, and Sutherland constants; Fluent material blocks are generated from it. |
| DC-008 | Must | SET-file line-number insertion is forbidden. SET is not a required input. |
| DC-009 | Must | Mesher is ANSA only. |
| DC-010 | Must | ISA model used only for h ∈ [0, 20] km. |

---

## Won't (v2)

| ID | Statement |
|----|-----------|
| WONT-001 | SU2 journals or submission. |
| WONT-002 | GUI. |
| WONT-003 | Author new UDF algorithms/C source from scratch; populating existing `.c` templates is required by FR-024. |
| WONT-004 | Scrape ANSA process logs **inside domain code**. The isolated meshlog-parser adapter (ADR-0010) is the single permitted interim metadata producer until the rewritten ANSA script emits structured metadata. |
| WONT-005 | Non-ISA atmospheres. |
| WONT-006 | Byte-compatible v01 matrix/SET/REF. |
| WONT-007 | Campaign matrix table (deferred — future layer per ADR-0006). |
| WONT-008 | Solver convergence checking and convergence-based early stopping in the current backend phase; revisit later. |
| WONT-009 | REF/matrix frontend parsing and refactoring the existing ANSA mesh-generation script in the current backend phase. |

---

## WISHLIST — promoted only via ADR

- Continuing or adding iterations at a specific interrupted/unconverged
  operating point remains deferred. Starting a new polar from a saved
  operating point is required by FR-032, not part of this wishlist.
- Solver convergence checking and criteria, deferred by the owner.
- Campaign matrix generation from / reconstruction to case files.
- Visualization session files (Fieldview/META).
