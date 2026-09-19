# JAMAL v2 — Documentation

> **Status:** Living. Read in this order.

**New starting point for the current review (2026-09-18):**
[Requisitos para o refactor completo em Python](<workshops/20260918-requisitos-legacy-analysis.md>)
documents the supplied shell/Python pipeline, its file contracts, 64 proposed
requirements, acceptance scenarios and readable JSON examples. It separates
confirmed decisions from observed behaviour and proposals. Physics and ANSA
metadata conflicts with earlier drafts are explicitly listed for resolution;
the new JSON examples are not an accepted schema or runnable cluster inputs.

| File | Question it answers |
|------|---------------------|
| `SCOPE.md` | Why, for whom, in/out, constraints |
| `DECISIONS.md` | Accepted decisions (ADR-0001…0012) — newest amendments take precedence |
| `REQUIREMENTS.md` | What the system shall do (testable, prioritised) |
| `TRACEABILITY.md` | Map between REQUISITOS RP-* IDs and FR/QA/OP/UX/DC IDs; ID status index |
| `ACCEPTANCE-SCENARIOS.md` | AC-01…20 — the living acceptance scenarios (tests reference these) |
| `SPECS.md` | Contracts and open details: JSON interface, equations, mesh metadata, config, solver input, post-processing |
| `LEGACY-SWEEP-INVENTORY.md` | Legacy sweep shapes: the ADR-0012 parity checklist |
| `WORKSHOPS.md` | Workshop outcomes + agendas for open specs |
| `OPEN-QUESTIONS.md` | Unsettled decisions (incl. D04–D08) + v01 pain we refuse to reintroduce |
| `GLOSSARY.md` | Shared domain vocabulary |
| `CONTRIBUTING.md` | How to propose changes; document hierarchy; PR/commit rules |
| `templates/ADR.md` | Copy-paste skeleton for a new ADR |
| `reviews/` | Dated codebase analyses (frozen at creation), e.g. `reviews/2026-09-19-codebase-analysis.md` |
| `workshops/` | Append-only meeting records + frozen analyses |
| `changelog/` | One file per requested change: `YYYY-MM-DD-NN-slug.md` (see AGENTS.md §4) |

## Rules

- **Placement:** if changing the syntax wouldn't change the shall, it
  belongs in `SPECS.md`, not `REQUIREMENTS.md`.
- A missing spec is a **defect**, not a license to guess (QA-001).
- Workshop outcomes get promoted via ADR or spec edit; do not implement
  syntax while a spec is still `Workshop`.
- Superseded ADRs are struck through in `DECISIONS.md`, never deleted.

## Current state

- **ADR-0007 sets the current boundary:** build the backend from JSON to
  solver execution and ADF post-processing. Matrix/REF authoring and
  parsing belong to the later frontend. Retain the existing ANSA script
  and its YAML interface; populate UDF templates with case-specific values.
- **ADR-0008 sets sweep behaviour:** one Fluent session, zero-seeded alpha
  branches, full iterations per computed point, and dependencies on saved source
  operating points. A saved first point is reused with no new iterations, as
  confirmed during shell analysis. Solver convergence checking is deferred.
- **ADR-0009 fixes atmosphere semantics:** geometric altitude, ISAD applied
  in every thermodynamic quantity; SPECS §2 is normative.
- **ADR-0010 fixes the mesh-metadata producer:** isolated meshlog parser
  behind a port; domain code never reads logs; swappable when the ANSA
  script is rewritten.
- **ADR-0011 seeds the numerics catalogue:** density-based
  (`fluent_density_based_v1`, from SET-050) and pressure-based
  (`fluent_pressure_based_v1`, from SET-055) profiles; the case file names
  the profile; journals are template-derived.
- **ADR-0012 sets the sweep parity baseline:** legacy branch semantics
  (zero-seeded branches, one-sided ranges, COLD per-point journals, Mach
  nesting, per-angle grids).
- Case input accepts **YAML or JSON interchangeably** (owner decision,
  2026-09-19); one schema, two encodings. Reference examples:
  [polar-0002.json](<examples/json-interface-draft/polar-0002.json>),
  [polar-0003.json](<examples/json-interface-draft/polar-0003.json>).
- Atmosphere equations (SPECS §2) are **normative** (ADR-0009); mesh
  metadata contract (SPECS §3) is normative with a swappable producer
  (ADR-0010).
- W1 (case-file schema) is the first implementation target.

## Pressing decisions & concerns

> Index only — one line per item, pointer to the owning section. Max 5
> items. Updated in the same commit whenever an ADR lands, a D-item
> closes, or the milestone changes (see AGENTS.md §4). All substance
> lives in the linked documents; **if this block vanishes, nothing is
> lost** — it can be rebuilt from OPEN-QUESTIONS + DECISIONS at any
> time.
>
> Last reviewed: 2026-09-19

**Co-owner decisions in flight** (either co-owner may decide; the
decision must be recorded as an ADR + changelog entry, which informs the
other):

1. **D05 — ADF contract** (needs external team sign-off) → blocks the
   post-processor; see [OPEN-QUESTIONS D05](<OPEN-QUESTIONS.md>) and
   [SPECS §9.1](<SPECS.md>).
2. **D08 — real inputs** (geometry/batch/templates to replace the
   placeholders) → blocks HPC parity testing; see
   [OPEN-QUESTIONS D08](<OPEN-QUESTIONS.md>).
3. **D04 — transform/morph translation limits** → blocks control-surface
   parity; see [OPEN-QUESTIONS D04](<OPEN-QUESTIONS.md>).

**Current work focus:**

4. **W1 — case-file schema** (first implementation milestone) → see
   [WORKSHOPS open agendas](<WORKSHOPS.md>) and [SPECS §1](<SPECS.md>).
5. **D07 — cluster integration** (`submit_fluent` vs direct PBS) → can
   start in parallel; see [OPEN-QUESTIONS D07](<OPEN-QUESTIONS.md>).

Maintainer note: if an item here contradicts OPEN-QUESTIONS or an ADR,
the other document wins and this list is stale — fix it immediately.

## History

This repository is the rebuilt home of the JAMAL v2 effort. The earlier
26-file doc-set (separate specs, ADRs, engineering standard, operations
handbook, manifest, rationale) was consolidated into the six core files
above; its full text lives in the git history of the previous
`refactor/rebuild` branch. The legacy v01 toolchain and the hybrid
Python/bash refactor are preserved under `JAMAL_shell/` and
`JAMAL_Struct_Folders/` as **frozen reference** — new v2 code starts
clean once W1 accepts the case-file schema. Legacy unit/integration
tests were removed from the package (several broken); recover them from
the owner's delivery archive if classification material is needed.
