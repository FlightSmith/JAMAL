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

## ADR-0009 — Atmosphere semantics: geometric altitude, ISAD everywhere [ACCEPTED]

**Decision (owner, 2026-09-19):** closes D01. The v2 ISA module uses
**geometric altitude** h ∈ [0, 20] km and applies ΔT_ISA (ISAD) consistently
in **all** thermodynamic quantities: T, p (inside the hydrostatic formula),
ρ, μ, and speed of sound. The legacy shell's `pressure_altitude` /
pressure-at-ISAD=0 behaviour is classified as a **convention of the old
tool**, not reproduced and not a compatibility goal (extends the v01-pain
closure R-01/R-02).

Consequences:

- SPECS §2.2–2.7 are promoted from review-hold draft to the normative
  physics contract, with the §2.1 REVIEW footnote resolved: R = 287.053
  J/(kg·K) (CIPM/ISO value; 287.05287 is the rounded form of the same
  constant) and p₁₁ = 22632.04 Pa accepted as the ISA tropopause pressure.
- The Reynolds→altitude inversion targets geometric altitude, with closure
  check per FR-014 (relative error < 1e-6) and bounded iterations.
- Golden-value tests use an approved reference (e.g. US Standard Atmosphere
  1976 tables) at 0, 11, and 20 km with ISAD = 0 and ≠ 0.
- FR-012/013 already matched this decision; no requirement edits needed.
- The old `SPECS §2` review hold is lifted; REQUISITOS RP-FL-05 is closed.

## ADR-0010 — Mesh metadata: isolated meshlog parser, structured output later [ACCEPTED]

**Decision (owner, 2026-09-19):** closes D02 for the current phase. Mesh
success/metadata continues to be derived from the ANSA meshlog in the
current phase, but **only** through one isolated, swappable module
(`meshlog parser` behind a `MeshMetadataSource` port). Domain code never
reads logs. When the ANSA script is rewritten (future phase), it will emit
a structured metadata file and the parser implementation is replaced;
neither the port nor any consumer changes.

Consequences:

- WONT-004 is amended: log **scraping inside domain code** remains
  forbidden; a bounded, isolated meshlog parser at the adapter edge is the
  accepted interim metadata producer (transitional exception, single
  implementation site).
- FR-016/FR-019 stand unchanged — they constrain what decides success
  (metadata contract), not which adapter fills it. The metadata contract
  (SPECS §3) is the port's output type.
- Producers/consumers label mismatch (`Fluid PIDs:` vs `Fluid: `) is
  handled inside the parser with a versioned normalization table.
- Acceptance: replacing the parser implementation with a structured-file
  reader requires no changes outside the adapter package.

## ADR-0011 — Numerics profiles: explicit solver family, template-derived journal [ACCEPTED]

**Decision (owner, 2026-09-19):** closes the recipe half of D08/RP-SO-02
for journal generation. The case file declares the solver family
explicitly (`density_based` | `pressure_based`) plus named settings; the
backend selects or auto-creates the Fluent numeric block from **versioned
templates**, one per supported profile. The profile catalogue is seeded
from the delivered SET pair:

- `fluent_density_based_v1` ← SET-050: density-based implicit, steady,
  flux-type 0, gradient `no no`, AMG-C 1, solution steering
  `subsonic`, divergence prevention on (0.1).
- `fluent_pressure_based_v1` ← SET-055: pressure-based, steady, flux-type
  `yes`, gradient `no yes`, high-order term relaxation enabled,
  pseudo-time-method global time step settings, no solution steering.

Consequences:

- The case file's `solver.numerics.profile` must name a profile from the
  catalogue (site config may add profiles); an unknown name → fail
  screaming. Default profile per campaign may be set in site config.
- Profiles own every numeric difference between SET-050/055; the legacy
  `TURB` choice (SA/SST/EULER/QCR/RC) remains a separate, orthogonal
  field. Only profiles with an emitted block are offered.
- AC-09 is testable: journals generated from both profiles must preserve
  the family-specific lines above, byte-stable (QA-004).
- Forbidden-enum gap (QCR/RC without emission branches, REQUISITOS §10)
  stays closed: enums list only what emits.

## ADR-0012 — Sweep policy: legacy branch semantics as parity baseline [ACCEPTED]

**Decision (owner, 2026-09-19):** closes D03's direction. Sweep ordering
and branching replicate the **legacy planner semantics** (jamal.sh case
sequence block) as the parity baseline, expressed through the explicit
plan artifact (RP-SW-01). Legacy shapes to reproduce:

1. Alpha sweep crossing zero (WARM): solve closest-to-zero point, save,
   positive branch away from zero, reload saved zero, negative branch —
   one session (equals ADR-0008 confirmed example).
2. Beta sweep crossing zero: same zero-seeded two-branch pattern with the
   sweep variable on beta (legacy outer-alpha/inner-beta nesting
   preserved).
3. One-sided alpha or beta range: single branch, starting at the end
   closest to zero, direction away from it (legacy `>= 0` / `< 0` forks).
4. Point at the zero index supplied by another polar (source case):
   loaded via `rc/rd` with **zero iterations** (FR-033 reuse rule);
   applicable at any point identity, not only alpha 0.
5. COLD strategy: independent initialization per point, one journal per
   point (no continue-solution chaining), same point order as WARM.
6. Mach sweep: outer loop over Mach values; alpha/beta sequences nest
   inside per legacy matrix semantics (KNITERS first/subsequent rule per
   Mach value).
7. Per-angle grids (aoa_grid) and multi-mesh: one journal per grid; far-
   field direction command emitted without angle components (grid carries
   the rotation); post-processing must not double-rotate (RP-ME-08).

Non-goals kept: no convergence gating (ADR-0008), no invented zero points,
no silent reordering. The plan artifact shows the expanded point list with
branch/reload provenance before submission (reviewable, deterministic).

Open follow-ups (do not block): explicit list inputs, ranges whose ends
are not reached by the step (reject per RP §6.1 proposal), negative-beta
branch confirmation in parity tests.

## Parked wishes (not shalls until promoted)

- **Continue iterations at an interrupted or unconverged operating point:**
  checkpoint selection and additional-iteration rules remain deferred.
  This excludes starting a new polar from a saved point, now required by
  ADR-0008.
- **Solver convergence checking:** criteria and any future effect on
  execution remain deferred. Current points run their full iteration count.
- **Matrix authoring layer:** generate case files from a table; optional
  reverse reconstruction. Spec: future MATRIX-SPEC.
