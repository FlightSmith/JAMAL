# Contributing to JAMAL v2

Multi-developer repository. Read `docs/README.md` first, in the order
given there. The short version of how work flows:

## Document hierarchy (what wins)

1. **ADR** (`docs/DECISIONS.md`) — accepted decisions, newest at the
   bottom, superseded text struck through, never deleted. An ADR may be
   amended only by a later ADR.
2. **Specs** (`docs/SPECS.md`) — contracts. Placement rule: if changing
   the syntax wouldn't change the shall, it belongs here, not in
   REQUIREMENTS.
3. **Requirements** (`docs/REQUIREMENTS.md`) — testable shalls with IDs.
4. **Open questions** (`docs/OPEN-QUESTIONS.md`) — undecided items. A
   missing spec is a defect, not a license to guess (QA-001).
5. **Workshops** (`docs/workshops/`) — append-only meeting records.
   Outcomes get promoted via ADR or spec edit, never implemented
   directly from a workshop note.

## Proposing a decision

1. Open a proposal issue or bring it to a workshop.
2. Record the outcome as an ADR entry (copy `docs/templates/ADR.md`).
3. Update the affected spec/requirement sections in the **same change**,
   so the documents never contradict the ADR.
4. Tick related `OPEN-QUESTIONS` boxes and reference the ADR.

## Code changes

- Branches: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
- PRs must state which requirement/spec/ADR they implement or amend.
  A code change that contradicts an ADR needs the ADR amended first.
- Domain code stays pure: no filesystem, environment, or subprocess
  access outside adapters (DC-006). No site-specific values in code
  (DC-004).
- Tests: golden artefacts (journals, plans) must be bit-stable (QA-004).

## Commits

Imperative mood, reference IDs: `FR-014: bound inversion iterations`.
Docs: `ADR-0009: geometric altitude semantics + SPECS §2 promotion`.

## Changelog

One file per requested change in `docs/changelog/YYYY-MM-DD-<slug>.md`,
two paragraphs max: what changed, what it touches.
