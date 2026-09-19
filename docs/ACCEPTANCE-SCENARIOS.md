# Acceptance scenarios — AC-01…AC-20

> **Status:** Living. Canonical English version of the acceptance
> scenarios, absorbed from the frozen analysis record
> ([20260918-requisitos-legacy-analysis.md](<workshops/20260918-requisitos-legacy-analysis.md>),
> §12.1). Tests reference these IDs. Update here — never in the frozen
> record. Status of blockers noted per row.

Owner decisions applied: AC-03 blocker D01 closed (ADR-0009); AC-08
metadata producer fixed (ADR-0010); AC-09 profile catalogue seeded
(ADR-0011).

| Test | Input / situation | Expected result |
|------|-------------------|-----------------|
| AC-01 | Case file equivalent to a simple case, no matrix/REF. | Validation and planning run; units and references appear in the resolved artefact. |
| AC-02 | Unknown field, duplicate key, conflicting unit, two sweeps, duplicate identity. | Localized failure before ANSA/PBS; no case disappears silently. |
| AC-03 | Mach/altitude vs Mach/Reynolds equivalence; 0, 11 and 20 km; non-standard ISA. | Agreement with approved reference (ADR-0009: US Std Atmosphere 1976 golden values); bounded inversion, closure check verified. ~~D01 blocker~~ closed by ADR-0009. |
| AC-04 | POLAR 0002, α=−10…20°, β=0. | 31 points, confirmed order, reload of 0 without extra iterations, one WARM session. |
| AC-05 | POLAR 0003 while 0002 still computes points after α0. | 0003 waits for α0 publication, reuses β0 with zero iterations, computes 15 new points; 16 data rows. Never calls ANSA. |
| AC-06 | Dependency on α=5°; dependency cycle; missing/failed source; partially written case/data. | Exact point selection; cycle/absence diagnosed; partial artefact never releases a dependent. |
| AC-07 | Same geometry/recipe in two runs; then change Y+ or batch content. | One shared mesh in the first case; different key in the second. No YAML contention. |
| AC-08 | Incomplete metadata, unknown negative-volume status, incompatible zones. | Never publish as valid mesh nor prepare wrong BCs. ~~D02 blocker~~ closed by ADR-0010 (isolated meshlog parser; golden metadata sample still needed). |
| AC-09 | Journals from `fluent_density_based_v1` (SET-050) and `fluent_pressure_based_v1` (SET-055); snippet injection and suppression. | Numeric choices preserved per ADR-0011, correct hooks, zero placeholders, missing injection target diagnosed. |
| AC-10 | CL/CY and MFR active/inactive; missing template. | Isolated sources and matching hooks; required-but-missing fails screaming; inactive mode compiles no UDF. |
| AC-11 | Job queued, cancelled, solver failed with transcript closed, lost submission response. | Distinct states; no false complete ADF, no automatic duplicate resubmission. |
| AC-12 | Crash after mesh, after submission, after solver; later ADF-only request. | Reconcile and resume by stages; active job preserved; post-process without re-solving. |
| AC-13 | Synthetic forces/moments with α/β=0 and non-zero; moment-centre shift; b≠c. | Approved signs, rotations and normalization; dimensionally consistent round trip. |
| AC-14 | Mach sweep with different q per point and overlapping zone groups. | Per-point q used; no double counting inside a group; nominal header values do not govern calculations. |
| AC-15 | ADF of 0003 at the reused point vs ADF of 0002 at the origin, same references. | Identical coefficients; provenance and zero additional iterations recorded. |
| AC-16 | Figures/Cp/loads disabled; then a requested optional product fails. | ADF independent of optional tools; selected failure reported separately in the summary. |
| AC-17 | Probes enabled. | No hidden iterations; plan and accounting reflect the approved sampling policy. |
| AC-18 | Two cases fail and one is disabled. | Coherent summary and exit code; no overall campaign success printed. |
| AC-19 | COLD, 2D, per-angle grids, representative controls and propulsion. | Specific parity approval per mode (see ADR-0012 + legacy sweep inventory); no extrapolation from the basic WARM scenario. |
| AC-20 | Historical consumer `prep_drag_rise.sh` with a homologated ADF. | Declared compatibility maintained, or migration/versioning explicitly agreed. |

## Sequencing (from the frozen record, §12.2 — still the working order)

1. Close contracts (W1 schema; ~~altitude/ISA~~ ADR-0009; ~~metadata
   producer~~ ADR-0010; ADF/eaxes D05; mode limits D06).
2. Core without HPC: models, validation, physics, plan, journal/UDF
   generation, post-processing with synthetic data → AC-01…04.
3. Mesh and execution: ANSA/PBS/Fluent adapters, isolation, cache,
   states → AC-05…12.
4. Full campaign 0002→0003 → AC-05, AC-15 end-to-end.
5. Parity and optional products → AC-13…20.
