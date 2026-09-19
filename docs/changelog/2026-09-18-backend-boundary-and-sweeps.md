# 2026-09-18 — Record backend boundary and confirmed sweep behaviour

## Context

The owner clarified the current JAMAL matrix example and answered the
requirements questions about JSON, ANSA, restart sources, iteration counts,
convergence, UDFs and post-processing.

## Changes

- Added ADR-0007 for the JSON backend boundary and existing tool integrations;
  retained superseded ADR-0006 clauses with strikethrough.
- Added ADR-0008 for sweep branches, full per-point iteration counts and
  dependencies on saved source operating points.
- Updated scope, requirements and specs to remove external REF and YAML
  case-input obligations, retain ANSA's YAML interface, populate UDF
  templates, and invoke dedicated ADF post-processing with optional figures,
  Cp and load distributions.
- Added FR-030/031/032 for branch initialization, fixed iterations and
  starting a dependent polar from a saved source point.
- Recorded the confirmed -10 to +20 alpha example: solve/save zero,
  positive branch, reload zero, negative branch, in one Fluent session.
- Deferred solver convergence checking; distinguished new-polar
  initialization from continuing an interrupted point's iterations.
- Updated the documentation index, glossary, open questions and workshop
  agendas; added `workshops/20260918.md` as a discussion summary.

## Validation and limits

Documentation-only changes; no implementation or solver tests were run.
Reviewed requirement identifiers, references and remaining contradictory
terminology. Earlier workshop records remain unchanged. Exact schemas,
tool contracts and source-readiness mechanics remain open; these edits do
not freeze them or claim that completed iterations establish convergence.
