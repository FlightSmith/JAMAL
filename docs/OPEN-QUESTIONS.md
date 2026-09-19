# JAMAL v2 — Open Questions

> **Status:** Living — not requirements. Also carries the v01-pain table
> (historical defects and where they are closed; do not reopen without an ADR).

The supplied implementation has now been analysed in
[Requisitos para o refactor completo em Python](<workshops/20260918-requisitos-legacy-analysis.md>).
Its D01–D08 group the remaining contracts and missing integration materials.
**Status update (2026-09-19):** D01 closed by ADR-0009, D02 closed by
ADR-0010, D03 direction set by ADR-0012 (legacy sweep semantics), and the
journal recipe catalogue seeded by ADR-0011. Remaining: D04, D05, D06, D07,
D08 (inputs).

---

## JSON backend interface (ADR-0007)

- [ ] Case-file schema per section (W1 — first implementation target)
- [x] Input encoding: YAML and JSON interchangeable (owner, 2026-09-19);
      one schema, two encodings. SPECS §1 updated.
- [ ] Resolved ISA values inside the case file vs pointer to a
      flow-conditions artefact
- [ ] Case-file naming convention (`{polar}.json` vs per-polar directory)
- [ ] State filename and whether the case file duplicates stage
- [x] Frontend/backend boundary: JSON; matrix/REF parsing is later frontend
      work. Existing YAML remains at the ANSA interface (ADR-0007).
- [ ] Campaign default unit if every value is suffixed anyway

- [x] Atmosphere acceptance reference, ISA-deviation pressure behaviour,
      geometric-altitude conventions → **closed by ADR-0009** (geometric
      altitude; ISAD in all quantities; golden values vs US Std Atmosphere
      1976). Coefficient axes/signs remain open under D05.
- [ ] Mesh metadata: ~~D02 producer conflict~~ closed by ADR-0010
      (isolated meshlog-parser adapter, swappable). Remaining: golden
      metadata sample for the parser tests.

## Product / ops

- [ ] Force re-run: which artefacts die?
- [ ] Mesh key: human `config_name` vs hash vs both
- [ ] In-process parallel EnsureMesh vs one process + PBS only
- [ ] Symlink across filesystems policy
- [ ] Installable CLI (`jamal …`)
- [ ] Re vs altitude: which direction is "primary" in docs/tests
- [ ] Exact iteration-count fields and legacy KNITERS mapping. Full
      iterations at every operating point are already decided (ADR-0008).
- [ ] Dedicated post-processing script contract and ADF format/compatibility
      (SPECS §9). Figures, Cp and load distributions are optional.
- [ ] Transform/morph grammar: reference kinds, units, ordering
      semantics (SPECS §1, workshop 20260910 — `t_`/`m_` prefixes
      dropped, transform/morph are separate sections now)
- [ ] Transformation-vector syntax: bare-name (`yz`, `xyz`) vs inline
      3-vector for point/direction; semantics of `None` as point
      (SPECS §1, workshop 20260916)
- [ ] `geometry.reference` schema: entry naming (AIRCRAFT/PROPELER),
      single-entry vs list, complete definitions provided through JSON
      (SPECS §1; external REF no longer a backend dependency)
- [x] What does the `config` spec cover? → site/tool configuration
      (SPECS §5; `CONFIG-SPEC.md` pre-consolidation) — closed 2026-09-10
- [x] Starting a new polar from another polar's saved operating point is
      required (ADR-0008); continuing an interrupted point remains deferred.
- [x] Its first saved point is reused without new iterations. POLAR 003
      reuses beta 0 and calculates beta 1…15 (ADR-0008 amendment, FR-033).
- [ ] Source-point identity, solution-file completeness/readiness, compatibility
      checks, dependency cycles, unavailable/failed sources and prior-campaign
      sources; source polar completion is not the readiness condition.
- [x] Sweep rules beyond the confirmed alpha example → direction closed by
      ADR-0012: legacy branch semantics are the parity baseline (zero-seeded
      branches, one-sided ranges, COLD, Mach nesting, per-angle grids).
      Residual: exact list-input syntax at W1.
- [ ] Existing ANSA YAML schema/invocation and metadata availability under
      the decision to keep the script unchanged.
- [ ] Proposed `01-GRIDS` scope/layout versus accepted shared cache and work
      roots; lock behaviour and ownership.
- [ ] Prepare-only boundary when a mesh or source solution is missing.

## Open decision IDs (D04–D08) — absorbed from the frozen analysis record

> Defined in
> [20260918-requisitos-legacy-analysis.md](<workshops/20260918-requisitos-legacy-analysis.md>)
> §13; tracked here. D01/D02 closed (ADR-0009/0010), D03 direction closed
> (ADR-0012).

- [ ] **D04 — Transform/morph grammar and ANSA translation.** Preserve
      references/vectors defined in the case file; map real operations to
      the retained script's positions and limits; confirm support for
      fractions, layers, and settings beyond current limits. Merges with
      the transform/morph grammar item above at W1.
- [ ] **D05 — ADF contract and aerodynamic conventions.** Owner obtains a
      real homologated ADF and its consumers; decide header/column/name/
      precision compatibility (3/4-digit identity), nominal-metadata
      handling; approve axes/signs/normalization. **This file is shared
      with an external team** — its format contract needs explicit
      versioning and their sign-off. Deliverable: SPECS §9 v1 + golden
      ADF. Legacy format reference (22 columns, 32 metadata fields) is
      recorded in SPECS §9.
- [ ] **D06 — Exact parity-mode set to retire legacy.** Confirm need and
      priority of COLD, 2D, per-angle grids, CL/CY drivers, fan/core/
      propeller and probes; close probe sampling budget. Sliding-mesh
      ANSA options do not prove solver support.
- [ ] **D07 — Cluster integration.** Provide `submit_fluent`
      contract/implementation or choose a direct PBS adapter; define
      modules/versions, queues, resources, environment, and per-point
      availability mechanism.
- [ ] **D08 — Real inputs per scenario.** Replace the placeholder
      `CARM.ansa` / `Batch_Scenario_carm.ansa` / `CARM.msh.h5` dummies
      with real geometry/batch/mesh; supply numbered templates and
      relevant geometries; `mfr.c` not located; `flowvis.ses`,
      `distclcp_meta.py`, `extract_alpha_beta_3.py` exist only in
      fixtures — validate versions/deployment if those modes are chosen.

## Deferred by the owner (not blockers for the current phase)

- Solver convergence criteria/checking and any later effect on execution.
  Current points always run their full specified iteration count.
- Continuing/adding iterations at an interrupted or unconverged point.
- Frontend implementation (including matrix/REF decisions) and refactoring
  the existing ANSA mesh-generation script.

## Already closed (do not reopen without an ADR)

- Mesh sharing + symlink + isolation — ADR-0001
- Resume Must, state + artefacts — ADR-0002
- SET not required; injection Must; suppression added — ADR-0003
- SU2 behaviour Won't; ports Must — ADR-0004
- Case-file-first model; matrix deferred — ADR-0006 (supersedes
  ADR-0005's table+YAML decision)
- JSON backend boundary; definitions/meshing inputs supplied through JSON;
  existing ANSA interface retained; populate UDF templates; dedicated ADF
  post-processing with optional figures/distributions — ADR-0007
- Zero-seeded positive/negative alpha branches, full iterations at every
  point, saved-source-point dependencies — ADR-0008
- Geometric altitude + ISAD everywhere; SPECS §2 normative — ADR-0009
- Isolated meshlog parser as interim metadata producer — ADR-0010
- Numerics profile catalogue (density/pressure based, from SET-050/055) — ADR-0011
- Legacy sweep semantics as parity baseline — ADR-0012
- YAML/JSON interchangeable case input — owner decision 2026-09-19 (SPECS §1)
- POL with suffix
- Unit suffixes in inputs
- Fluent this year

---

## v01 pain we refuse to reintroduce (historical)

| Old ID | Pain | Closed by |
|--------|------|-----------|
| R-01 | Pressure computed with ISAD=0 | P-ACC-01 |
| R-02 | Density mixed ISAD | P-ACC-02 |
| R-03 | Sutherland constants expressed two ways | P-ACC-03, DC-007, FR-027 |
| R-04 | Newton inlined S=110.4 | P-ACC-04 |
| R-05 | Altitude ft vs m confusion | DC-001, UX-001 |
| R-06 | SET insertion by line number | DC-008, ADR-0003 |
| R-07 | REF no schema | W1 JSON engineering definitions, FR-008; REF parsing outside backend |
| R-08 | Non-monotonic sweeps | W1 |
| R-09 | No inversion closure | FR-014 |
| R-10 | `from_dict` swallows exception types | ES-009 |
| R-11 | Batch swallows errors, no summary | QA-006, OP-006 |
| R-12 | Committed `.venv` / coverage | engineering standard |
| — | All meshes in one folder; parallel runs corrupt | ADR-0001, QA-002 |
| — | No resume | ADR-0002 |

Do not implement "bash temperature with ISAD forced to 0" compatibility.
