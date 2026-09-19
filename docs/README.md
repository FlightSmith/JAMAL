# JAMAL v2 — Documentation

> **Status:** Living. Read in this order.

**New starting point for the current review (2026-09-18):**
[Requisitos para o refactor completo em Python](<C:/Users/User/Documents/ChatGPT/JAMAL 2/docs/REQUISITOS-REFACTOR-PYTHON.md>)
documents the supplied shell/Python pipeline, its file contracts, 64 proposed
requirements, acceptance scenarios and readable JSON examples. It separates
confirmed decisions from observed behaviour and proposals. Physics and ANSA
metadata conflicts with earlier drafts are explicitly listed for resolution;
the new JSON examples are not an accepted schema or runnable cluster inputs.

| File | Question it answers |
|------|---------------------|
| `SCOPE.md` | Why, for whom, in/out, constraints |
| `DECISIONS.md` | Accepted decisions (ADR-0001…0008) — newest amendments take precedence |
| `REQUIREMENTS.md` | What the system shall do (testable, prioritised) |
| `SPECS.md` | Contracts and open details: JSON interface, equations, mesh metadata, config, solver input, post-processing |
| `WORKSHOPS.md` | Workshop outcomes + agendas for open specs |
| `OPEN-QUESTIONS.md` | Unsettled decisions + v01 pain we refuse to reintroduce |
| `GLOSSARY.md` | Shared domain vocabulary |
| `workshops/` | Meeting/brainstorm records, append-only (see AGENTS.md) |
| `changelog/` | One summary per requested change (see AGENTS.md) |

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
- Equations (SPECS §2) and mesh metadata (SPECS §3) remain drafts;
  physical conventions and existing-script compatibility need review.
- W1 (case-file schema) is the first implementation target.

## History

This branch (`refactor/rebuild`) previously held the full 26-file doc-set
(separate specs, ADRs, engineering standard, operations handbook, manifest,
rationale). It was consolidated into the six files above; the full text is
in git history (commit 53e5080 and earlier on this branch, plus the
v01-evolved code on `main`).

## Legacy note

The v01-evolved Python code on `main` (`app/`, `bin/`, `tests/`) is
**frozen as reference** for the v2 rebuild. New v2 code starts clean once
W1 accepts the case-file schema.
