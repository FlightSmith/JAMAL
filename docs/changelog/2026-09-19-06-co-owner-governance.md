# 2026-09-19-06 — Co-owner governance + pressing-decisions block hardening

Governance correction: the project has two co-owners (rajado and his
senior partner). Either co-owner may decide any open decision alone;
the deciding party's agent/harness must record it in the same change as
an ADR plus a changelog entry, so the other co-owner is informed by the
repo, not by conversation. "Unrecorded decisions are not decisions."
Replaces the previous "owner-only decisions" framing.

docs/README.md pressing-decisions block: renamed section to "Co-owner
decisions in flight"; every item now links to its owning document
(OPEN-QUESTIONS D-id, SPECS sections, WORKSHOPS); added "Last reviewed"
date stamp; block explicitly deletable-by-design (rebuildable from
OPEN-QUESTIONS + DECISIONS).

AGENTS.md §4: block rules updated with the ownership clause, link
requirement, and last-reviewed date rule.

Touches: docs/README.md, AGENTS.md.
