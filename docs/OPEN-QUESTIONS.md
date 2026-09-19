# JAMAL v2 — Open Questions

> **Status:** Living — not requirements. Also carries the v01-pain table
> (historical defects and where they are closed; do not reopen without an ADR).

The supplied implementation has now been analysed in
[Requisitos para o refactor completo em Python](<C:/Users/User/Documents/ChatGPT/JAMAL 2/docs/REQUISITOS-REFACTOR-PYTHON.md>).
Its D01–D08 group the remaining contracts and missing integration materials.
In particular, D01 requires clarifying altitude/ISA semantics before using
the historical pressure/temperature defect labels below as a physical oracle.

---

## JSON backend interface (ADR-0007)

- [ ] Case-file schema per section (W1 — first implementation target)
- [ ] Resolved ISA values inside the case file vs pointer to a
      flow-conditions artefact
- [ ] Case-file naming convention (`{polar}.json` vs per-polar directory)
- [ ] State filename and whether the case file duplicates stage
- [x] Frontend/backend boundary: JSON; matrix/REF parsing is later frontend
      work. Existing YAML remains at the ANSA interface (ADR-0007).
- [ ] Campaign default unit if every value is suffixed anyway

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
- [ ] Sweep rules beyond the confirmed zero/positive/reload-zero/negative
      alpha example: one-sided ranges, lists, negative beta, Mach and no-zero
      ranges. Do not invent additional zero points without a decision.
- [ ] Existing ANSA YAML schema/invocation and metadata availability under
      the decision to keep the script unchanged.
- [ ] Proposed `01-GRIDS` scope/layout versus accepted shared cache and work
      roots; lock behaviour and ownership.
- [ ] Prepare-only boundary when a mesh or source solution is missing.
- [ ] Atmosphere acceptance reference, ISA-deviation pressure behaviour at
      sea level/11 km, geometric-altitude conventions, and coefficient axes/signs.

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
