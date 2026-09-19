# AGENTS.md — operating guide for agents and harnesses

> Target audience: AI coding agents (Claude Code, Codex, Cursor, Hermes,
> …) and their human handlers working in this repository. Read this whole
> file before touching anything. It defines what you may do, in what
> order, and what you must never do.

## 1. Repository map

```text
docs/                     Living documentation — the source of truth
  README.md               Start here; reading order and doc index
  SCOPE.md                Why, for whom, in/out of scope
  DECISIONS.md            ADR-0001…NNNN — accepted decisions, append-only
  REQUIREMENTS.md         The only shall-list (FR/QA/OP/UX/DC/WONT IDs)
  TRACEABILITY.md         RP-*/AC-* ↔ FR-* map and ID status
  ACCEPTANCE-SCENARIOS.md AC-01…20 — scenarios tests reference
  SPECS.md                Contracts: interface, physics, mesh, journal, ADF
  OPEN-QUESTIONS.md       What is undecided (incl. D04–D08)
  GLOSSARY.md             Domain vocabulary
  LEGACY-SWEEP-INVENTORY.md  Legacy sweep shapes (ADR-0012 parity checklist)
  CONTRIBUTING.md         Human workflow: branches, PRs, ADR process
  templates/ADR.md        Skeleton for a new ADR
  reviews/                Dated codebase analyses (frozen at creation)
  workshops/              Append-only meeting records + frozen analyses
  changelog/              One file per requested change (naming below)
JAMAL_shell/              FROZEN hybrid bash/Python refactor — reference only
JAMAL_Struct_Folders/     FROZEN reference data (matrix, REF/SET, placeholders)
```

**`JAMAL_shell/` and `JAMAL_Struct_Folders/` are frozen references for the
v2 rebuild.** Do not modify them except to correct a factual file error
(e.g. a bad filename). Never "improve" legacy code.

## 2. Reading order (mandatory, in this order)

1. `docs/README.md`
2. `docs/SCOPE.md`
3. `docs/DECISIONS.md` — newest ADRs take precedence
4. `docs/REQUIREMENTS.md`
5. `docs/SPECS.md` — sections relevant to your task
6. `docs/OPEN-QUESTIONS.md` — so you don't re-ask decided things
7. `docs/TRACEABILITY.md` + `docs/ACCEPTANCE-SCENARIOS.md` if you touch
   requirements or tests

Skipping this order is how contradictions get reintroduced.

## 3. Precedence rules (what wins)

If documents conflict, precedence top-down:

1. `docs/DECISIONS.md` (ADRs — newest amendment wins)
2. `docs/SPECS.md` (contracts)
3. `docs/REQUIREMENTS.md` (shalls)
4. `docs/workshops/20260918-requisitos-legacy-analysis.md` — **frozen**
   historical record; informative only, never normative. Its RP-*/AC-*
   IDs are stable but their status lives in TRACEABILITY.
5. Everything else (reviews, changelog, workshop notes) is history.

A missing spec is a **defect**, not a license to guess (QA-001). If the
answer isn't in the docs, ask the owner or file it in OPEN-QUESTIONS —
do not invent behaviour.

## 4. How to make changes

### Code (v2 backend, when it exists)

- Domain modules stay pure: no filesystem, environment, subprocess, or
  tool imports (DC-006). Adapters isolate ANSA/Fluent/PBS/LMOD.
- No site-specific paths, module names, or versions in code (DC-004).
- Fail screaming: invalid input → immediate, descriptive error. No
  partial silent output, no leftover placeholders (QA-001).
- Golden artefacts (journals, plans) must be bit-stable (QA-004).
- State which requirement/spec/ADR you implement in the PR description.

### Documentation

- New accepted decision → append an ADR to `DECISIONS.md` (use
  `templates/ADR.md`), and update the affected spec/requirement sections
  **in the same commit**. Tick related OPEN-QUESTIONS boxes.
- Syntax-level change (wouldn't change a shall) → SPECS.md, not
  REQUIREMENTS.md.
- Superseded ADR text is struck through, never deleted.
- Every requested change gets one file in `docs/changelog/`.

### Changelog naming

`docs/changelog/YYYY-MM-DD-NN-slug.md` — **NN is a two-digit sequence
per day**, starting at `01`, in the order changes were committed that
day. Example: `2026-09-19-01-doc-harmonization-decisions.md`. Slug:
lowercase, hyphens, max ~5 words. Never reuse or edit old entries;
append-only.

### Workshop records

Append-only under `docs/workshops/`. A session record is added, then its
outcomes are promoted via ADR/spec edits. Do not implement syntax or
behaviour while its spec is still `Workshop`.

## 5. Prohibitions (hard)

- Do not edit frozen legacy trees (`JAMAL_shell/`, `JAMAL_Struct_Folders/`)
  except for factual file errors.
- Do not rewrite or delete changelog/workshop entries; append-only.
- Do not renumber requirement IDs (FR/QA/AC/RP/D/ADR). New items take the
  next free number.
- Do not resolve an OPEN-QUESTIONS item in code. It becomes an ADR first.
- Do not introduce a second place for the same contract (one home per
  question; cross-link instead).
- Do not commit secrets, credentials, or site-internal URLs.
- Do not implement behaviour for items whose spec status is `Workshop`.
- No log scraping outside the isolated meshlog-parser adapter (ADR-0010).

## 6. Commit conventions

Imperative mood; reference IDs when applicable:

```text
FR-014: bound inversion iterations
ADR-0009: geometric altitude semantics + SPECS §2 promotion
docs: fix changelog naming scheme
```

Multi-developer repo: branches `feat/<topic>`, `fix/<topic>`,
`docs/<topic>`; PRs preferred over direct pushes to `main`; a PR that
contradicts an ADR must amend the ADR first.

## 7. Verification before you claim done

- Link check: every `](<path>)` style link in `docs/**/*.md` resolves
  (relative to the file's directory).
- New/changed JSON or YAML parses.
- ADR additions update: DECISIONS.md + affected specs + OPEN-QUESTIONS
  checkboxes + TRACEABILITY (if IDs/status changed) + one changelog file.
- `git status` clean; pushed to `origin/main` when the task is complete.
