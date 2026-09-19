# Glossary

> **Status:** Living. Domain words only — no requirements, no formulas, no file grammars. Definitions referenced by `REQUIREMENTS.md` and `SPECS.md`.

---

**Case file**  
The JSON document holding engineering data and artefact references for one simulation/polar (ADR-0006/0007). The frontend/backend boundary: parsed, schema-validated, then executed stage by stage. Matrix/REF interpretation belongs to the later frontend. See FR-001, `SPECS.md` §1.

**Campaign**  
A set of case files prepared and run together in one invocation. Parsed, validated, then materialised one case file per simulation. A text-table *matrix* generating/deriving case files is a deferred future layer.

**Case / entry**  
One operating-point (or sweep-of-points) entry after parse/validation/sweep expansion; a case may contain a sweep run as one job. Identified by POL.

**POL**  
Case identity: 4-digit base `0000`–`9999` plus optional alphanumeric suffix (`0001a`, `0001b`). Unique within a campaign. See UX-002, FR-003.

**REF**  
An aircraft/geometry definition file used by the current JAMAL (reference dimensions, control-surface counts and names, etc.). Its future existence and format are frontend concerns. The backend receives the relevant definitions through JSON. See FR-008, IF-002 and ADR-0007.

**Operating point**  
One set of flight conditions within a polar, with its specified iteration count and resulting solution. A sweep consists of multiple operating points.

**Sweep branch**  
A sequence of operating points executed in one Fluent session, each continuing from the preceding solution. In the confirmed alpha sweep, the positive and negative branches both originate from a saved zero-angle solution. See ADR-0008 and `SPECS.md` §6.1.

**Source-point solution**  
The saved mesh and flow solution of a specified operating point used to initialize another polar. Its availability, rather than completion of the source polar, determines readiness of the dependent polar. See FR-032 and `SPECS.md` §6.2.

**ADF**  
Aerodynamic data file produced by a dedicated post-processing script, containing three force and three moment coefficients in each of the body, wind and stability axes. See FR-028 and `SPECS.md` §9.

**SET**  
v01 Fluent journal template. **Not required** in v2 (ADR-0003; replaced by builder/templates + injection).

**ISAD**  
ISA temperature deviation (offset from the International Standard Atmosphere). Density, pressure and temperature are always evaluated at the *same* ISAD. Valid with geometric altitude 0–20 km. See FR-012–FR-015, DC-010.

**Work root**  
Unique directory created for every JAMAL invocation. All mutable artefacts (journals, logs, state file, results, summary) live under it. Shared inputs are read-only or write-once. Enables concurrent campaigns. See OP-003, QA-002, ADR-0001.

**Mesh artefact / mesh key**  
The volume mesh file together with its valid mesh-metadata; the mesh key identifies a shareable mesh (geometry + mesh parameters). Cases that share geometry + mesh parameters share **one** artefact (symlink, not copy). Success is decided only from metadata + `mesh_path` existence. See FR-017–FR-020, ADR-0001.

**Injection / injection pack**  
Explicit, versioned extra solver-input (snippets, overrides, additional files) supplied by the operator when the generated Fluent journal is insufficient. Missing path is a hard failure. SET files are not required. See FR-023, ADR-0003.

**Stage**  
A named step in the per-case lifecycle (parse → mesh → journal → submit → monitor → post-process). Resume continues from the last *successful* stage. See OP-001, OP-005, ADR-0002.

**Sref, Cref, Bref**  
Reference area, chord, span — code uses domain names internally.

**Fail screaming**  
Invalid input, missing file, schema-invalid artefact, leftover placeholder, or failed external tool produces an immediate, descriptive error. No partial silent output, no guessed columns. See QA-001.

Tokens `CREF`, `SREF`, `ISAD` appear at the I/O boundary only.
