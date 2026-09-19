# Traceability — REQUISITOS RP-* ↔ v2 requirement IDs

> **Status:** Living. The RP-* IDs are the legacy-analysis proposal space
> (2026-09-18); FR/QA/OP/UX/DC are the v2 requirement IDs. This table is
> the bidirectional map so neither document has to be read side-by-side
> with the other. `—` means the RP has no separate FR (covered by a spec
> or future workshop deliverable).

| RP (REQUISITOS §5) | v2 IDs | Notes |
|--------------------|--------|-------|
| RP-IN-01 | FR-001, IF-002 | JSON-only backend |
| RP-IN-02 | FR-002, FR-005 | Schema + cross-field validation, fail screaming |
| RP-IN-03 | FR-001, UX-003 | Domain names, real types |
| RP-IN-04 | UX-002, FR-003 | Identity; point IDs not rounded-name based |
| RP-IN-05 | OP-002 | Run flags; input never used as state |
| RP-IN-06 | UX-001, DC-001 | Unit suffixes, SI internal |
| RP-IN-07 | QA-001 | Path resolution base, existence checks |
| RP-IN-08 | FR-006 | One sweep variable per case |
| RP-IN-09 | FR-008, FR-009 | Referential integrity of controls/vectors/groups |
| RP-FL-01 | FR-012, FR-015 | Flow-condition resolution, persistence |
| RP-FL-02 | FR-007, FR-014 | Mode compatibility, Re inversion |
| RP-FL-03 | FR-014, DC-010 | Bounded inversion, closure < 1e-6 |
| RP-FL-04 | FR-027, DC-007 | Single constants source, same Sutherland in journal |
| RP-FL-05 | FR-012, FR-013 | **Closed by ADR-0009** (geometric altitude) |
| RP-ME-01 | FR-016, FR-032 | Three mesh origins |
| RP-ME-02 | FR-018 | JSON→YAML adaptation, archived effective YAML |
| RP-ME-03 | QA-002, QA-003 | Isolated ANSA workspace, env restore |
| RP-ME-04 | ADR-0001, FR-020 | Content-key cache |
| RP-ME-05 | QA-008 | Serialize same-key creation, publish only valid |
| RP-ME-06 | FR-019, SPECS §3 | Metadata contract; **producer fixed by ADR-0010** |
| RP-ME-07 | FR-009, SPECS §8 | Transform/morph mapping limits |
| RP-ME-08 | FR-009 | Per-angle grids; no double rotation |
| RP-ME-09 | SPECS §1 | Mesh-design vs flight conditions separation |
| RP-SW-01 | SPECS §6.1, ADR-0012 | Explicit plan artifact |
| RP-SW-02 | FR-022, FR-030 | Zero-seeded branches, one session |
| RP-SW-03 | FR-031 | Full iterations, no convergence gating |
| RP-SW-04 | FR-033 | Reused point, zero iterations, provenance |
| RP-SW-05 | FR-032 | Wait for point, not polar |
| RP-SW-06 | SPECS §6.2 | Source compatibility checks |
| RP-SW-07 | FR-032, QA-001 | Cycle/absence detection, blocked dependents |
| RP-SW-08 | ADR-0012 | No invented points; policy visible in plan |
| RP-SW-09 | SPECS §6.1 | COLD = independent init per point |
| RP-SW-10 | FR-029 | Probes; no hidden iterations |
| RP-SO-01 | FR-021 | Complete journal from named profile (ADR-0011) |
| RP-SO-02 | FR-021, ADR-0011 | Profile catalogue seeded from SET-050/055 |
| RP-SO-03 | FR-025, FR-026 | BC groups by declared identity, not prefixes |
| RP-SO-04 | FR-022, SPECS §2.8 | Flow direction from α/β; grid-rotation provenance |
| RP-SO-05 | FR-023 | Injection + suppression, no line numbers (DC-008) |
| RP-SO-06 | FR-024 | UDF template population |
| RP-SO-07 | FR-024 | CL/CY driver bookkeeping |
| RP-SO-08 | FR-026 | Propulsion BC definitions |
| RP-EX-01 | OP-001, OP-004 | Execution modes, resume, status |
| RP-EX-02 | OP-005 | PBS adapter, stored job identity (D07 open) |
| RP-EX-03 | QA-009 | Distinct run states; transcript marker insufficient |
| RP-EX-04 | ADR-0002 | State persistence, no duplicate jobs |
| RP-EX-05 | ADR-0002 | Stage resume without re-solving |
| RP-EX-06 | QA-003, QA-007 | Tool invocation records, LMOD isolation |
| RP-EX-07 | QA-006, OP-006 | Summary, exit codes, fail-fast semantics |
| RP-EX-08 | QA-002, ADR-0001 | Work roots, atomic publication |
| RP-PP-01 | FR-028 | Dedicated postprocessor, invocable standalone |
| RP-PP-02 | FR-028 | Per-point q; six coefficients, three axis systems |
| RP-PP-03 | FR-025 | Symmetry half-area; documented conventions (D05 open) |
| RP-PP-04 | QA-001 | Every point once; no zero-filling gaps |
| RP-PP-05 | FR-028 | Total + component ADFs (D05 open) |
| RP-PP-06 | FR-028 | Optional products fail separately |
| RP-PP-07 | FR-029 | Probe bookkeeping |
| RP-QA-01..08 | QA-001..QA-010 | Direct counterparts; RP-QA-08 → testability without HPC |
| AC-01..20 | — | Acceptance scenarios; tests reference these IDs directly |

## Requirement ID ordering note

FR-028/FR-029 (post-processing) were numbered after FR-027 but are listed
after FR-033 in `REQUIREMENTS.md` (they were added later in draft
history). IDs are stable; do **not** renumber — new requirements take the
next free number regardless of section. The section ordering is cosmetic.
