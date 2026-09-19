# JAMAL v2 — Scope

> **Status:** Accepted intent (updated for ADR-0007/0008 backend boundary and sweeps)

---

## 1. Purpose

Automate the lifecycle of external-aerodynamics CFD simulation campaigns on
HPC. The current refactoring phase is the **backend**, starting at a
**JSON case file, one per simulation/polar**, and ending with execution and
post-processing: validate, resolve atmosphere/flow, obtain a mesh or saved
solution, emit solver input, submit, resume, and produce ADF results when
post-processing is requested.

The **frontend** is a later phase. Matrix authoring and REF parsing, if
retained, happen before the JSON boundary. The backend receives reference
quantities and other engineering definitions through JSON, independent of
whether a REF file exists.

## 2. Users

Aerodynamicists and CFD operators on a shared Linux HPC project volume.
They must be able to run more than one campaign/invocation at a time
without corrupting meshes or results.

## 3. Constraints

| ID | Constraint |
|----|------------|
| C-01 | Primary solver: ANSYS Fluent. |
| C-02 | Mesher: ANSA. No alternative. |
| C-03 | Scheduler: PBS with LMOD modules. |
| C-04 | ISA atmosphere valid 0–20 km only. |
| C-05 | Platform: HPC Linux cluster. |
| C-06 | SI internally; convert at the I/O boundary. |
| C-07 | Site paths, module names, tool versions: configuration, not code. |

## 4. In scope (v2)

- JSON case interface + schema-driven validation.
- ISA atmosphere, Sutherland viscosity, Mach↔velocity, Re↔altitude
  inversion with closure check.
- Mesh obtain/reuse/share via symlink; JSON-to-YAML adaptation for the
  existing ANSA script, which continues handling transformations/morphing.
- Fluent journal emission with injection (add **and** suppress commands).
- Sweeps within one Fluent session, with the full specified iterations at
  each computed point; zero-seeded positive/negative alpha branches per SPECS §6.1.
- Starting a dependent polar from a saved source operating point as soon
  as that solution is available, without rebuilding its grid. Reuse that
  first point without new iterations (ADR-0008 amendment).
- Populate existing UDF `.c` templates with case-specific values.
- PBS submit; prepare-only / submit / submit+monitor+post-process.
- ADF generation through a dedicated post-processing script; flow figures,
  Cp and load distributions are optional.
- Resume from last successful stage per case; concurrent isolated runs.
- Structured logging and end-of-run summary.
- Design seam so SU2 can be added next year without touching domain code.

## 5. Out of scope (v2)

| Item | Notes |
|------|-------|
| Campaign matrix table | Future layer (ADR-0006); generate-from and derive-to are separate future specs |
| Frontend / REF parsing | Later phase; backend engineering inputs arrive through JSON (ADR-0007) |
| Refactoring the ANSA script | Use its current YAML interface and transformation/morphing behaviour for now |
| Solver convergence checking | Deferred; every point currently runs its full specified iterations (ADR-0008) |
| GUI / web interface | — |
| Mesh quality optimisation | ANSA's job |
| Non-ISA atmospheres | — |
| Generating UDF C source from scratch | UDF `.c` files are templates; they are updated during the process to generate a `.c` with the correct values |
| SU2 behaviour | Won't v2; ports stay |
| v01 matrix/SET/REF byte-compatibility | Not a goal |

## 6. Spec documents

| Document | Status |
|----------|--------|
| `SPECS.md` §1/§2/§3 — JSON case interface, equations, mesh metadata | Draft; exact contracts and physics still require review |
| `SPECS.md` §5 — site/tool configuration (`site`, `tools`, `paths`, `defaults`, `physics.constants_profile`) | Workshop |
| `SPECS.md` §6 — solver-input | Workshop |
| `SPECS.md` §4 (REF), §7 (matrix) | Out of scope — no v2 workshop |
| `SPECS.md` §9 — post-processing / ADF | Outcome accepted; script and file contracts open |

> Note (2026-09-10): "config" in earlier tables meant the site/tool
> configuration spec (`CONFIG-SPEC.md` pre-consolidation) — now SPECS §5.
> Not to be confused with the `geometry.configuration` field in the case
> file, which is the aircraft configuration/flavour.
