# JAMAL v2 — Workshops

> **Status:** Process log. Agendas for open workshops; outcomes recorded
> below and promoted via ADR / spec edits. Newest outcome first.

---

## Outcome — Legacy analysis 20260918 (requirements from supplied code)

The owner changed the investigation strategy: analyse `JAMAL_shell` and
`JAMAL_Struct_Folders`, then document requirements for a full Python backend
replacement while preserving the readable JSON interface.

**New confirmed decision:** reuse the first point from a saved source
solution without new iterations; POLAR 003 calculates beta 1…15 after
reusing beta 0. Promoted to the ADR-0008 amendment and FR-033.

**Deliverable:**
[Requisitos para o refactor completo em Python](<workshops/20260918-requisitos-legacy-analysis.md>),
with traceable requirements, acceptance scenarios, draft JSON examples and
explicit conflicts with earlier atmosphere/metadata drafts. Proposed
contracts are not automatically promoted to accepted ADRs.

**Record:** `workshops/20260918-shell-analysis.md`.

---

## Outcome — Clarification 20260918 (backend boundary and execution)

**Decisions (promoted: ADR-0007/0008, requirements and specs):**

1. Build the backend first, from a JSON interface through solver execution
   and post-processing. Matrix/REF handling belongs to the later frontend.
2. JSON supplies meshing parameters, geometry references and engineering
   definitions. Retain the existing ANSA script and its YAML interface;
   the script continues handling transformations and morphing.
3. A sweep runs in one Fluent session. For alpha -10 to +20 by 1: solve
   and save 0, run +1…+20, reload 0, run -1…-10.
4. Every point runs its full specified iterations. Solver convergence
   checking/criteria are explicitly deferred and do not gate the sweep.
5. A new polar may start from another polar's saved operating point; wait
   for that point's solution, not for the source polar to finish. This is
   separate from continuing an interrupted point's iterations.
6. Populate existing UDF `.c` templates. Invoke a dedicated post-processing
   script for ADF production; figures, Cp and load distributions are optional.

**Record:** `workshops/20260918.md`; reference example: the real matrix file
[matrixpy](<../JAMAL_Struct_Folders/matrixpy>).
Exact schemas, tool invocation and source readiness contracts remain open.

---

## Outcome — Workshop 20260916 (transformation vectors, reference block, mesh workspace)

**Decisions (promoted: SPECS §1 edits, new SPECS §8):**

1. Transform/morph references (`hr_1`, `ha_1`, …) must be defined in the
   case file under `geometry.transformation_vector` as a
   `[point, direction]` pair; existence verified at load, fail early on
   missing references.
2. Hard-coded axis shortcuts (`none`, `x`, `y`, `z`, `xy`, `xz`, `yz`,
   `xyz`) usable as point/direction shorthands.
3. Reference quantities (`geometry.reference`): AIRCRAFT block
   (SREF/CREF/BREF/XREF/YREF/ZREF) and PROPELER block
   (NBLADES/DIAM/CHORD/HUB/TILT).
4. Mesh workspace layout: `./01-GRIDS/{GEOM, BATCH_SCENARIO, GRIDS}`
   with a lock in `GRIDS` against multi-user generation collisions.
   → new SPECS §8.

**Brainstorm captured:** see `workshops/20260916.md`. Grammar detail
questions (bare-name vs inline vector syntax, reference-block schema)
added to SPECS §1 Open.

---

## Outcome — Workshop 20260910 (case-file model)

**Decisions (promoted: ADR-0006, ADR-0003 amendment):**

1. Start development and tests from a **self-contained JSON/YAML case file
   per simulation** (MATRIX + REF + YAML unified in one model). → ADR-0006.
2. Individual validation of fields via **schema** (JSON Schema).
3. All validations run **after** the JSON generation (parse → schema →
   cross-field).
4. Injection must support a **wildcard/hook field** for arbitrary
   user-defined strings at specific journal positions (e.g. before mesh
   read, after turbulence model definition). → SOLVER-INPUT-SPEC hook points.
5. Injection must also support **removing existing generated commands**,
   not only adding. → ADR-0003 amendment.

**Wishlist (parked, see REQUIREMENTS WISHLIST):**

- Restart and continue iterations from a specific α/β (low-convergence
  case or Fluent crash).
- New iterations restart from their own α, or any α at user request.

**Brainstorm captured:** transform/morph grammar
(`t_r:he_1:20,t_s:p_1:50:t_t:x:50:m_r:he_1:20`) — see SPECS §1. Status:
idea only, not accepted.

---

## Open agendas

### W1 — Case-file schema (was: matrix)

Goal: accept SPECS §1 v1 and implement parse → validate.
Order: sections and field list → modes/exclusivity → units and suffixes →
POL identity → transform/morph grammar (accept or reject) → engineering
definitions formerly in REF → meshing and source-solution fields → per-point
iterations → nulls and disable flag → JSON encoding rules.
Exit: valid example, invalid examples, versioning rules; FR-001..FR-011
point at a real spec.

### W2 — Aircraft definition (REF): deferred to frontend

No separate REF-format workshop in the current backend phase (ADR-0007).
Required physical data, surface/propulsion definitions, reference identities,
units and validation now belong to the JSON interface under W1.

### W3 — Solver input + injection

Goal: accept SPECS §6 v1; close ADR-0003 option B vs C.
Order: every value that must appear in a journal → builder vs template
pack → hook points (incl. wildcard position fields) → **suppression
mechanism** → injection artefact schema → UDF template population and hooks
→ fixed-iteration branch execution → saved-source-point readiness and loading
→ Fluent version command syntax → golden dumps for reviewers.
Exit: golden journal excerpt; leftover-token test; injection-missing and
suppression tests.

### W-config — Site/tool configuration schema

Goal: accept SPECS §5 v1 (JSON Schema + startup validation).

### W-postprocess — Dedicated script and ADF contract

Goal: accept SPECS §9, including required solver artefacts, script invocation,
ADF structure and optional outputs. Solver convergence checking is deferred.
