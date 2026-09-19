# JAMAL v2 — Specifications

> **Status:** Mixed. Each spec carries its own status. Equations and
> mesh-metadata are carried over near-verbatim from the accepted drafts;
> the rest are compressed to decisions + open points (full text lives in
> git history on `main` and in this branch's history).

---

# 1. JSON case interface — per simulation/polar

> **Status:** Workshop → first implementation target (ADR-0006/0007).
> Backend boundary accepted; exact JSON schema not yet frozen.
>
> **Encoding (owner, 2026-09-19):** YAML and JSON are **interchangeable
> encodings** of the same case model — either is accepted as input because
> YAML supports comments and reads better by eye; JSON remains the
> canonical machine boundary (schema, examples, resolved artefacts).
> The schema is encoding-agnostic; one schema version per case-file
> format. Reference examples are kept in JSON:
> [polar-0002.json](<examples/json-interface-draft/polar-0002.json>),
> [polar-0003.json](<examples/json-interface-draft/polar-0003.json>).

## Decisions taken

- One **JSON file per simulation/polar**: identity, aircraft definitions
  and reference quantities, geometry references + morphing/transform ops,
  control surfaces, propulsion BC groups, flight conditions, numerics,
  meshing parameters, initialization/source-solution references, injection
  pointers and run flags. A polar may contain a sweep.
- JSON is the frontend/backend interface. Matrix and REF interpretation
  belong to the later frontend; no REF file is required by the backend.
  Existing YAML remains an ANSA tool interface, not a second required
  backend input encoding.
- Field-level validation is **schema-based** (JSON Schema); all validation
  happens **after** parsing into the schema structure.
- Schema versioning: semver; parser accepts `1.x.x`; unknown major → hard
  fail.
- Domain names in the file (`angle_of_attack_deg`, `reference_area`),
  solver tokens only where the operator must see them.
- Hinge/morph references (`he_1`, `p_1`, …) and surface/propulsion arities
  must resolve against the definitions supplied in JSON, with checks at load.
- The backend resolves flow conditions from these inputs, including CREF
  when Reynolds number is supplied instead of altitude.

## Required sections (draft)

The YAML sketches below preserve earlier workshop notation for discussing
field structure. They are not valid backend input examples or an accepted
JSON schema. Meshing, initialization and iteration fields still need exact
contracts; valid JSON examples are a W1 deliverable.

~~~yaml
schema_version: "1.0.0"
identity: { polar: "0001a", campaign_id: …, run_id: … }
aircraft: { name: … }
geometry:
  configuration: …
  transformation_groups:
    AILERON_RH: ['W\.AIL.*_RH']
    AILERON_LH: ['W\.AIL.*_LH']
    WING: ["W.*"]
  infout_groups:
    BODY: ["b_", "b\."]
    AILERON: 'W\.AIL.*'
control_surfaces:
  transform: {'RUDDER': ['r:hr_1:20', 's:p_1:50'], 'AILERON': ['r:ha_1:20'], … }
  morphing: {'AILERON': ['r:ha_1:20'], 'WING_TIP': ['t:x:50'], … }
propulsion: { fan_inlet: […], … }
flight:
  spec: { mach: …, reynolds: …, isa_deviation_k: … }
  # resolved: filled by ResolveFlow stage
numerics: { turbulence: SA, solver: fluent, … }
injection: { journal_snippets: […], suppressions: […], extra_files: […] }
~~~

## Transform/morph grammar (workshop 20260910 — supersedes 20260902 brainstorm)

The `t_`/`m_` operation prefixes are **dropped**. Transform and morph are
now separate sub-sections of `control_surfaces` (`transform:` /
`morphing:`), each a map from group name to a list of operations.

Operation syntax (unchanged within an operation):
`r`/`s`/`t` (rotate/scale/translate) + reference + amount, e.g.
`r:hr_1:20` (rotate about hinge-line rudder 1, 20 deg), `s:p_1:50`
(scale from point 1, factor 50), `t:x:50` (translate along x, 50 mm).

**Fail-early rule:** before emitting solver input, every group name used
in `control_surfaces.transform` must be verified against
`geometry.transformation_groups` / `infout_groups` at load time. In the
example above, `RUDDER` does not exist in `geometry` — the case file
fails validation, not the Fluent run.

### Transformation vectors (workshop 20260916)

Every reference used by a transform/morph operation (`hr_1`, `ha_1`,
`p_1`, …) must be **defined in the case file** under
`geometry.transformation_vector`, and its existence is verified at load
time — a missing reference fails validation, not the solver run. Each
item is a `[point, direction]` pair, where each element is a 3-vector
(e.g. `ha_1: [[5,6,7],[0,1,0]]` — vector at point [5,6,7] pointing +y).

Hard-coded axis shortcuts, usable wherever a point or direction is
expected:

| Name | Vector | | Name | Vector |
|------|--------|--|------|--------|
| `none` | [0,0,0] | | `xz` | [1,0,1] |
| `x` | [1,0,0] | | `yz` | [0,1,1] |
| `y` | [0,1,0] | | `xyz` | [1,1,1] |
| `z` | [0,0,1] | | | |
| `xy` | [1,1,0] | | | |

~~~yaml
geometry:
  transformation_vector:
    ha_1: [[5,6,7],[0,1,0]]
    3d: [None,xyz]
    yz: [[0,0,0],yz]
    y: [[0,0,0],y]
~~~

### Reference block (`geometry.reference`, workshop 20260916)

Aircraft and propulsion reference quantities live in the case file under
`geometry.reference`:

~~~yaml
geometry:
  reference:
    AIRCRAFT:
    - SREF:  2.231   # ref area
      CREF:  0.500   # ref chord
      BREF:  2.786   # ref span
      XREF:  1.598   # moment centre
      YREF:  0.000
      ZREF:  0.000
    PROPELER:
    - NBLADES: 2
      DIAM: 1
      CHORD: 0.1
      HUB: [5,6,7]
      TILT: [0,1,0]
~~~

## Open

1. Exact schema of each section (this is the first implementation task).
2. Resolved ISA values inside the file vs pointer to a flow-conditions
   artefact.
3. JSON file naming convention (`{polar}.json` vs a per-polar directory).
4. Relationship to the state file (embed stage vs separate `state.yaml`).
5. Transformation-vector details: bare-name vs inline-vector syntax for
   the point/direction pair (`3d: [None,xyz]` uses `None` for a point);
   whether the axis shortcuts are the only allowed shorthand.
6. `geometry.reference` schema: section names (AIRCRAFT / PROPELER —
   note the source's spelling "PROPELER"), one entry vs list semantics,
   and complete engineering definitions formerly read from REF.
7. Fields for meshing parameters, geometry assets, source operating-point
   identity, saved solution references and per-point iteration counts.

---

# 2. Equations & physics

> **Status:** Normative (ADR-0009, 2026-09-19 — closes D01). All quantities
> SI unless noted. v01 bugs are not the spec; the legacy shell's
> pressure-altitude / pressure-at-ISAD=0 convention is not reproduced.

## 2.1 Constants (single source of truth — DC-007)

One Python module defines these. No other file may invent values.

| Symbol | Value | Unit | Description |
|--------|-------|------|-------------|
| γ | 1.4 | — | Ratio of specific heats |
| R | 287.053 | J/(kg·K) | Specific gas constant, dry air (CIPM/ISO; 287.05287 is the same constant rounded) |
| g | 9.80665 | m/s² | Standard gravity |
| p₀ | 101325 | Pa | ISA sea-level pressure |
| T₀ | 288.15 | K | ISA sea-level temperature |
| h₁₁ | 11000 | m | Tropopause |
| p₁₁ | 22632.04 | Pa | ISA tropopause pressure (accepted, ADR-0009) |
| T₁₁ | 216.65 | K | ISA tropopause temperature |
| L | −0.0065 | K/m | Tropospheric lapse rate |
| μ_ref | 1.716×10⁻⁵ | Pa·s | Sutherland reference viscosity |
| T_ref | 273.11 | K | Sutherland reference temperature |
| S | 110.56 | K | Sutherland constant |

> The earlier REVIEW on R and p₁₁ is resolved by ADR-0009. Fluent
> `sutherland three-coefficient-method` is generated from the same numbers.

## 2.2 Temperature

Inputs: geometric altitude h (m), ISA deviation ΔT_ISA (K).

~~~
if h ≤ h11:  T(h) = T0 + ΔT_ISA + L·h
else:        T(h) = T11 + ΔT_ISA
~~~

## 2.3 Pressure — ISAD **in** the hydrostatic formula

~~~
if h ≤ h11:
    T_local = T0 + ΔT_ISA + L·h
    p(h) = p0 × (T0 / T_local)^(g / (L·R))
else:
    T_local = T11 + ΔT_ISA
    p(h) = p11 × exp[−g / (R·T_local) × (h − h11)]
~~~

**Acceptance (P-ACC-01):** `pressure(h, ISAD)` uses `T(h, ISAD)`, never
`T(h, 0)`.

## 2.4 Density

~~~
ρ(h) = p(h, ΔT_ISA) / (R · T(h, ΔT_ISA))
~~~

**Acceptance (P-ACC-02):** both p and T at the same ISAD.

## 2.5 Dynamic viscosity (Sutherland, three-coefficient form)

~~~
μ(T) = μ_ref × (T / T_ref)^(3/2) × (T_ref + S) / (T + S)
~~~

Root-finders and Reynolds numbers **call this function**; never inline S.
**Acceptance (P-ACC-03):** one Sutherland triple; Fluent material generated
from it.

## 2.6 Speed of sound & Mach ↔ velocity

~~~
a(T) = √(γ·R·T)      V = M·a(T)      M = V / a(T)
~~~

## 2.7 Reynolds–altitude inversion

Given M, Re, C_ref, ΔT_ISA → find h ∈ [0, 20] km via Newton (or
equivalent) on T, then map T→h through the ISA profile. Constants from
§2.1; μ from §2.5. **Closure (FR):** recompute Re after inversion; relative
error < 1e-6, else fail screaming. Stratosphere T→h uses the isothermal
hydrostatic relation consistently with §2.3.

## 2.8 Unit vector (flow direction)

~~~
α_rad = α·π/180;  β_rad = β·π/180
ex =  cos(β)·cos(α)
ey = −sin(β)
ez =  cos(β)·sin(α)
~~~

> REVIEW: ~~confirm e_y sign~~ **Resolved (2026-09-19):** e_y = −sin(β)
> confirmed against the legacy implementation (`unit_vector_comp` in
> [utils.sh](<../JAMAL_shell/lib/utils.sh>)) and Fluent pressure-far-field
> convention.

## 2.9 Acceptances

| ID | Rule |
|----|------|
| P-ACC-01 | Pressure uses T(h, ISAD). |
| P-ACC-02 | Density uses p and T at the same ISAD. |
| P-ACC-03 | One Sutherland triple; Fluent material generated from it. |
| P-ACC-04 | Inversion calls μ(T); closure check required. |
| P-ACC-05 | All internal computation SI; conversion only at the I/O boundary. |

---

# 3. Mesh metadata (JSON)

> **Status:** Draft 1.0.0 — parser-normative. Producer for the current
> phase: isolated meshlog-parser adapter behind the `MeshMetadataSource`
> port (ADR-0010); the rewritten ANSA script will replace it with a
> structured file later, without changing this contract. Full
> field-by-field text lives in git history
> (`docs/specs/MESH-METADATA-SPEC.md`); carried here: the contract.

- ANSA batch produces a process log (ignored) and a **mesh metadata JSON**
  (parsed). JAMAL v2 never scrapes the log.
- Accept: `schema_version` 1.x.x, `volume_mesh_ok == true`,
  `negative_volume_count == 0`, `errors` empty. Anything else = failed
  mesh; skip solver generation for that case; no guessing.
- Cross-checks: `sum(cells_by_type) == topology.cells`;
  `quality.cell_volume.negative_count == status.negative_volume_count`;
  `bounding_box.min[i] < max[i]`.
- `boundaries` array: unique names; symmetry handling (Sref/2) looks up by
  configured name.
- Quality thresholds are configuration, not parser constants.

---

# 4. REF input (future frontend)

> **Status:** Deferred outside the current backend phase (ADR-0007).

Whether a separate REF file exists, and its encoding or authoring workflow,
are future frontend decisions. The backend must not read it.

Required engineering data instead belong to the JSON contract in §1:
reference area/chord/span and moment centre; surface identities, counts
and transformation vectors; propulsion definitions; symmetry/boundary
information and geometry references. Coordinate and unit conventions
still need to be specified there.

---

# 5. Site / tool configuration

> **Status:** Workshop. Validated at startup; fail screaming on unknown
> validator names; no hardcoded site values in domain code (DC-004/005).

Candidate sections: `site` (scheduler, modules), `tools` (ansa, fluent:
module/executable/version), `paths` (mesh_cache_root, udf sources),
`defaults` (altitude_unit, polar_width), `physics.constants_profile`
(names a profile; values are never duplicated here).

---

# 6. Solver input (Fluent journal + injection)

> **Status:** Behaviour in §6.1/§6.2 accepted (ADR-0008, ADR-0012); journal
> numerics profiles accepted (ADR-0011); exact injection and saved-solution
> contracts remain Workshop (W3). SET is not required as an input
> (ADR-0003).

Product obligations: complete journal, no leftover placeholders; swept
Mach/α/β → sequential operating points in **one** journal; injection
(snippets at hook points, override map, extra files) **and suppression of
generated commands** (workshop 20260902); UDF `.c` templates updated to
generate a `.c` with the correct values only when the corresponding mode
is active; Sutherland in journal = ISA module; fan/core BC groups with
JSON-validated arity; symmetry halves Sref.

## 6.0 Numerics profiles (ADR-0011)

The case file declares the solver family and profile explicitly; the
backend selects or auto-creates the numeric block from **versioned
templates**. Seeded catalogue (derived from the delivered SET pair):

| Profile | Source | Family | Defining lines |
|---------|--------|--------|----------------|
| `fluent_density_based_v1` | SET-050 | density-based implicit | `/solve/set/flux-type 0`; gradient `no no`; AMG-C `1`; solution steering `subsonic`; divergence-prevention `enable 0.1` |
| `fluent_pressure_based_v1` | SET-055 | pressure-based | `/solve/set/flux-type yes`; gradient `no yes`; high-order term relaxation `enable yes`; pseudo-time-method global time step `no 10` |

Rules: `solver.numerics.profile` names a catalogue entry (site config may
register more); unknown name → fail screaming. Turbulence model (SA / SST /
EULER) is orthogonal to the profile. Journals generated from each profile
are golden-test artefacts (QA-004 bit-stable).

## 6.1 Sweep execution and iterations

Run a sweep in one Fluent session. Within each branch, changing alpha or
beta updates the far-field velocity direction; the next point continues
from the current solution without closing Fluent or reinitializing.

**General policy (ADR-0012):** sweep ordering and branching replicate the
legacy planner semantics as the parity baseline — zero-seeded two-branch
pattern for any alpha/beta sweep crossing zero; single branch starting at
the end closest to zero for one-sided ranges; COLD = one journal per point,
independent initialization; Mach sweeps nest alpha/beta per matrix
semantics; per-angle grids emit one journal per grid without angle
components in the far-field command. See ADR-0012 for the full shape list.

Confirmed example, alpha -10 to +20 degrees in steps of 1:

1. Run alpha 0 for its specified iterations and save its solution.
2. Run alpha +1, +2, …, +20, continuing from each preceding solution.
3. Reload the saved alpha 0 solution in the same Fluent session.
4. Run alpha -1, -2, …, -10, continuing from each preceding solution.

This produces 31 distinct operating points. Reloading zero does not run
zero's iterations again. The two branches both start from the saved zero
solution; the negative branch does not inherit the +20 solution.

Every computed point runs its **full specified iteration count**, not a maximum
subject to convergence-based early exit. Solver convergence checks and
criteria are deferred. Completing the requested iterations is not a claim
that the flow solution has physically converged. Tool failures remain
errors under QA-001. Numerical closure checks for flow-condition inversion
in §2 are separate and remain required.

Open: explicit point lists; ordering when a source-point replaces the
near-zero seed; exact iteration fields and how legacy KNITERS maps to them.

## 6.2 Starting a dependent polar from a saved solution

Confirmed example: POLAR 003 sweeps beta 0 to 15 degrees in steps of 1,
at alpha 0. Its first point starts from POLAR 002's saved alpha 0 solution
(beta 0, Mach 0.2, altitude 0 ft), including that solution's mesh. No new
grid is generated for this restart. Subsequent beta points continue within
POLAR 003's Fluent session.

**Confirmed during shell analysis (2026-09-18):** the saved first point is
reused without new iterations. POLAR 003 therefore records beta 0 from the
source and calculates beta 1 through 15: 16 result points, 15 newly computed.
Its first-computed-point iteration count applies to beta 1. Preserve source
provenance and record zero additional iterations at the reused point.

Wait for the requested source-point solution to be saved and available.
Completion of the entire source polar is not the dependency. Source-point
identity, saved-file completeness, compatibility checks and readiness
signalling need an exact contract before implementation; an in-progress
file write must not be treated as an available solution.

This is initialization of a new polar from a saved point. Continuing the
iterations of an interrupted point is a separate deferred feature, while
stage-level resume remains required by ADR-0002.

Generated UDF sources are case-specific files populated from existing
templates. Keep template inputs unchanged; emit compilation/loading hooks
only for the corresponding active modes.

## 6.3 Remaining journal contract

Open: builder vs versioned template pack; hook-point names; suppression
mechanism; Fluent version command syntax.

---

# 7. Campaign matrix (future layer — NOT v2)

> **Status:** Deferred (ADR-0006). Placeholder so the idea has a home.

A text table that **generates** case files before a run, or is
**reconstructed** from the case files of past runs. Requires the case-file
schema to be frozen first. Do not build until a spec workshop accepts it.

---

# 8. Mesh generation workspace (workshop 20260916)

> **Status:** Directory layout remains Workshop. Existing-script integration
> accepted under ADR-0007.

The JSON case supplies meshing parameters and geometry references. Adapt
these to the YAML consumed by the existing ANSA mesh-generation script.
Continue to use that script unchanged for transformations, morphing and
meshing; refactoring it is later work. Its YAML schema, invocation and
ability to supply §3 metadata still need to be documented/verified.

Proposed structure under `./01-GRIDS`:

- `GEOM/` — all geometries common to the simulation campaign.
- `BATCH_SCENARIO/` — ANSA batch-scenario files with the instructions
  for generating the mesh.
- `GRIDS/` — mesh generation results, intermediate files, generation
  logs, and a **`lock`** to avoid collisions between multiple users
  generating meshes concurrently.

The lock aligns with ADR-0001 (concurrent invocations never write the
same mutable path) and QA-002 (run isolation).

The relationship of this proposed directory layout to ADR-0001's mesh
cache and isolated work roots remains open; the proposal does not replace
the accepted sharing/isolation requirements.

---

# 9. Post-processing and ADF

> **Status:** Output responsibility accepted (ADR-0007); script/file contracts open.

After solver execution, the backend invokes a dedicated post-processing
script to produce an aerodynamic data file (ADF). The ADF contains three
force and three moment coefficients in each of the body, wind and stability
axis systems. Flow visualization figures, Cp and load distributions are
optional and are not prerequisites for producing the ADF.

Open: script inputs/invocation, required solver artefacts, ADF schema and
compatibility with existing consumers, axis/sign and normalization
conventions, optional-output selection, and treatment of partial sweeps.
Solver convergence classification is deferred and is not required now.
