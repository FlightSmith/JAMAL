# JAMAL v2

Rebuild of JAMAL — Job Automation and Management of Aerodynamic
simuLations (CFD) — as a Python backend that takes one case file per
simulation/polar and drives the full campaign lifecycle: validate →
resolve flow conditions → obtain/reuse meshes (ANSA) → emit Fluent
journals → submit (PBS) → monitor → post-process to ADF.

| Directory | Content |
|-----------|---------|
| [`docs/`](docs/README.md) | **Living documentation — start here** |
| `JAMAL_shell/` | Frozen hybrid bash/Python refactor (reference only) |
| `JAMAL_Struct_Folders/` | Frozen reference data: matrix, REF/SET, ANSA configs |

## Status

Pre-implementation: contracts and decisions are being frozen. The
documentation set is complete and internally consistent; the first code
milestone is W1 (case-file schema). Open decision IDs D04–D08 are tracked
in `docs/OPEN-QUESTIONS.md`.

Constraints: ANSYS Fluent + ANSA + PBS/LMOD on a Linux HPC; SI internally;
YAML or JSON case input (one schema, two encodings).

## Reading order

1. [`docs/README.md`](docs/README.md) — doc map and rules
2. [`docs/SCOPE.md`](docs/SCOPE.md) — purpose, users, in/out
3. [`docs/DECISIONS.md`](docs/DECISIONS.md) — accepted decisions (ADRs)
4. [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) — the shall-list
5. [`docs/SPECS.md`](docs/SPECS.md) — contracts

Contributing: [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).
AI agents and harnesses: read [`AGENTS.md`](AGENTS.md) before operating
in this repository.

## The legacy trees

`JAMAL_shell/` (3k-LoC bash + phase-1/2 Python hybrid) and
`JAMAL_Struct_Folders/` (matrix, support files, ANSA YAML contract) are
**frozen references** for the rebuild. Do not modify them; their
behaviour is analysed in
[`docs/workshops/20260918-requisitos-legacy-analysis.md`](docs/workshops/20260918-requisitos-legacy-analysis.md).

## License

See [LICENSE](LICENSE).
