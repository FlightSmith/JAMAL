# Legacy sweep-shape inventory (parity checklist for ADR-0012)

> **Status:** Reference. Extracted from the legacy planner
> ([jamal.sh](<../JAMAL_shell/bin/jamal.sh>) case-sequence block) so the
> ADR-0012 parity baseline has a concrete checklist. Each row must either
> be reproduced in v2 (with a parity test) or have an explicit owner
> decision to drop.

| # | Legacy shape | Trigger in legacy code | v2 handling (ADR-0012) | Parity test |
|---|--------------|------------------------|------------------------|-------------|
| 1 | Alpha sweep crossing zero, WARM | zero inside range, `START=WARM` | Zero-seeded two-branch pattern (ADR-0008 example) | AC-04 |
| 2 | Beta sweep crossing zero, WARM | zero in beta, alpha fixed | Same pattern, sweep variable beta; outer-alpha/inner-beta nesting preserved | new |
| 3 | One-sided alpha range | `alpha[0] >= 0` or all `< 0` forks | Single branch from the end closest to zero, direction away | new |
| 4 | One-sided beta range | beta `>= 0` / `< 0` forks | Same as #3 for beta | new |
| 5 | Source-point at the zero index | `start_from_polar_case` + `rc/rd` | Any point identity may be sourced; zero iterations on the reused point (FR-033) | AC-05, AC-06 |
| 6 | COLD strategy | `START=COLD` | One journal per point, independent initialization, no chaining | AC-19 |
| 7 | Mach sweep | `len(mach) > 1` outer loop | Outer Mach loop; α/β nest inside; KNITERS first/subsequent per Mach | AC-14 |
| 8 | Per-angle grids (`aoa_grid`) | grid names with `aoa` marker | One journal per grid; far-field command without angle components; no double rotation in post | AC-19 |
| 9 | Multi-mesh files | `len(grid) > 1` non-aoa | One journal per grid, grid-specific SET suffix | AC-19 |
| 10 | Velocity mode input | `MACH[VEL]` bracketed `[...]` | Mach↔velocity conversion at resolved conditions (FR-015) | AC-03 |
| 11 | 2D (planar) cases | `dim != 3d` journal branches | Out of core scope; parity decision pending (D06) | AC-19 |
| 12 | CL/CY driver modes | `ALPHA[CLS]` / `BETA[CYS]` | UDF `coef_driver.c` population (FR-024); controller tolerance ≠ convergence | AC-10 |

## Non-reproduced legacy behaviours (deliberate)

| Legacy behaviour | Reason not reproduced |
|------------------|----------------------|
| Matrix mutated during submission (`sed` on RUN column) | Input-as-state banned (RP-IN-05); state lives in the run state file |
| Point names from rounded Mach/Re/angles (`M20RE24AL+010…`) | Collision-prone (RP-IN-04); v2 point IDs come from the plan artifact |
| `while true` physics loops without caps | Bounded iterations + closure check required (FR-014) |
| Inconclusive negative-volume check treated as OK | Fail-screaming: unknown ≠ valid (RP-ME-06, AC-08) |
| p evaluated at ISAD=0 while T/ρ/μ use ISAD | Convention conflict closed by ADR-0009 (geometric altitude, ISAD everywhere) |

## residual open points (from ADR-0012)

- Explicit point-list syntax (vs range) — W1.
- Range end not reachable by step: reject (RP §6.1 proposal) — confirm at W1.
- Negative-beta branch: confirm behaviour in parity tests.
- Source-point seed replacing the near-zero point when they differ — SPECS §6.1 Open.
