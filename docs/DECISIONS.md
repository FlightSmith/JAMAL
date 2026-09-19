# JAMAL v2 — Accepted Decisions

> **Status:** Living. Newest at the bottom. An ADR may be superseded by a later one; superseded text is kept, struck through, not deleted.

---

## ADR-0001 — Mesh sharing and run isolation [ACCEPTED]

Same geometry + mesh parameters → **one** mesh artefact, cached write-once
under `cache/meshes/<mesh_key>/`. Other cases reference it by **symlink**
(never copy). Concurrent invocations never write the same mutable path: each
invocation gets a unique **work root** (`runs/<run_id>/`); only the cache
`create` of the *same* key needs serialisation.

## ADR-0002 — Resume: state file + artefact presence [ACCEPTED]

Resume is **Must**. An interrupted campaign continues from the last
successful **stage** per case. Resume uses **both** a state file and
artefact presence/validity. Conflict → fail screaming or a documented
reconcile rule. A failed mesh does not invalidate a successful parse;
post-process can be requested later without re-solving.

## ADR-0003 — Journal generation and user injection [ACCEPTED]

SET is **not required**. JAMAL emits a complete, valid Fluent journal
(builder and/or versioned templates — not v01 SET) plus a mandatory
**injection** mechanism: extra snippets at documented hook points, an
override map for named parameters, and additional files, all explicit and
versioned with the case. Missing referenced injection artefact → fail
screaming.

**Amendment (workshop 20260902):** injection must also support
**removal/suppression** of generated commands, not only addition. Mechanism
to be fixed in the solver-input spec.

## ADR-0004 — Solver ports; SU2 deferred [ACCEPTED]

Solver access goes through a port (`Mesher` / `Solver` / `Scheduler`).
Fluent is the v2 implementation; ANSA is the only mesher; PBS is the
scheduler. SU2 behaviour is **Won't (v2)** — but adding it must not change
case, ISA, or campaign-parsing code.

## ADR-0005 — Campaign table + per-case YAML [SUPERSEDED by ADR-0006]

~~Campaign is authored as one text table (the Matrix); each entry
materialises as one per-case YAML record.~~ Superseded by ADR-0006. The
matrix survives only as a future derivation/authoring layer (see ADR-0006).

## ADR-0006 — Case file first: one self-contained case per simulation [ACCEPTED; amended by ADR-0007]

**Decision (workshop 20260902, confirmed by the owner):** development and
tests start from a **self-contained case file** ~~(JSON or YAML)~~ (JSON,
per ADR-0007) holding all
data required for one simulation: identity, geometry/morphing, control
surfaces, propulsion BCs, flight conditions, numerics, mesh instruction,
injection pointers. Field-level validation is **schema-based**; all
validation runs *after* the file is parsed into that structure.

Consequences:

- The matrix (text table) is **deferred**: later, a tool may generate case
  files from a matrix, or reconstruct a matrix from the case files of past
  runs. Neither is a v2 shall until a spec freezes it.
- ~~REF data (reference dimensions, hinge lines, surface/propulsion arities)
  is referenced by the case file and validated against it; REF encoding is
  W2 business, but the case-file schema is written so the linkage is
  checkable.~~ Superseded by ADR-0007: these definitions arrive through JSON;
  a separate REF file is not a backend dependency.
- One schema version per case-file format; unknown major → hard fail.
- ~~JSON and YAML are both acceptable encodings of the same model; pick per
  file, schema is encoding-agnostic.~~ Superseded by ADR-0007: JSON is the
  frontend/backend interface. Existing ANSA YAML remains a tool interface.

## ADR-0007 — Backend first, with a JSON interface [ACCEPTED]

**Decision (owner clarification, 2026-09-18):** refactor in two parts.
The current part starts at JSON and ends with solver execution and
post-processing. The future frontend prepares that JSON; matrix authoring
and whether/how REF files exist belong to that later part.

- JSON supplies engineering definitions, reference quantities, geometry
  references, meshing parameters, flight conditions and execution inputs.
  The backend performs calculations such as resolving flow conditions
  from Mach, Reynolds number and CREF without parsing a REF file.
- Keep the existing ANSA script, including its transformation and morphing
  behaviour, unchanged for now. Adapt JSON meshing inputs to its existing
  YAML interface. Refactoring that script is later work.
- Populate existing UDF `.c` templates with case-specific values. Generated
  sources belong to the isolated case workspace; shared templates are inputs.
- A dedicated post-processing script produces the ADF, containing three
  force and three moment coefficients in each of the body, wind and
  stability axes. Flow figures, Cp and load distributions are optional.

Exact JSON, tool invocation and ADF contracts remain to be specified.

## ADR-0008 — Fluent sweep branches, fixed iterations and source-point dependencies [ACCEPTED]

**Decision (owner clarification, 2026-09-18):** a sweep executes in one
Fluent session. Within a branch, the journal updates the far-field
velocity direction and runs the specified iterations from the current
solution.

- For the confirmed alpha sweep from -10 to +20 degrees in steps of 1:
  solve and save 0; run +1 through +20; reload the saved 0 solution; run
  -1 through -10. Both branches remain in the same Fluent session.
- Every computed operating point runs its full specified iteration count. Do not
  advance early on convergence. Solver convergence checking and criteria
  are deferred; they do not gate subsequent points in this phase.
- A polar may start from another polar's saved operating-point solution.
  In the example, POLAR 003's beta sweep starts from POLAR 002 at alpha 0,
  reusing the saved mesh and solution without generating a new grid.
  The dependency is on that saved source point becoming available, not
  on completion of the entire source polar.
- Starting a new polar from a saved solution is required. Continuing an
  interrupted point's iterations is a separate, still-deferred capability;
  stage-level resume under ADR-0002 remains required.

Ordering outside the confirmed alpha example, source compatibility checks,
and the mechanism for publishing source-point readiness remain open.

**Amendment (owner confirmation during shell analysis, 2026-09-18):** when
the first point is another polar's saved solution, reuse that point without
new iterations. POLAR 003 therefore reuses beta 0 from POLAR 002 and starts
its new iterations at beta 1. It has 16 result points, of which 15 are newly
computed. Record source provenance and zero additional iterations for the
reused point. This qualifies the fixed-iteration rule; it does not introduce
convergence-based early stopping.

## Parked wishes (not shalls until promoted)

- **Continue iterations at an interrupted or unconverged operating point:**
  checkpoint selection and additional-iteration rules remain deferred.
  This excludes starting a new polar from a saved point, now required by
  ADR-0008.
- **Solver convergence checking:** criteria and any future effect on
  execution remain deferred. Current points run their full iteration count.
- **Matrix authoring layer:** generate case files from a table; optional
  reverse reconstruction. Spec: future MATRIX-SPEC.
