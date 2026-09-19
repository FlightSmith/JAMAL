# 2026-09-19 — Documentation harmonization + decisions ADR-0009..0012

Owner decisions applied: geometric altitude + ISAD everywhere (ADR-0009,
closes D01), isolated meshlog parser as interim metadata producer
(ADR-0010, closes D02), numerics profile catalogue seeded from SET-050/055
(ADR-0011), legacy sweep semantics as parity baseline (ADR-0012), and
YAML/JSON interchangeable case input.

Doc fixes: all dead ChatGPT-export links rewired (link check clean);
README History rewritten for this repo; AGENTS.md / jamal_matrix.jpeg
references replaced (CONTRIBUTING.md, `matrixpy`); SPECS §2 promoted to
normative with constants resolved; SPECS §1/§6 updated (encoding, §6.0
profiles, §6.1 legacy sweep policy); SCOPE in/out updated; OPEN-QUESTIONS
closed items ticked with ADR references.

New files: `CONTRIBUTING.md`, `templates/ADR.md`, `TRACEABILITY.md`
(RP↔FR map), `LEGACY-SWEEP-INVENTORY.md` (12 legacy sweep shapes as
parity checklist). Examples updated: `numerics.profile` renamed to
`fluent_density_based_v1` + explicit `solver_family` field.

Touches: DECISIONS.md, REQUIREMENTS.md, SPECS.md, SCOPE.md, README.md,
OPEN-QUESTIONS.md, ANALYSIS-2026-09-19.md, examples/*.json, workshops/*,
examples README.
