# 2026-09-19 — Placeholder filenames: strip erroneous `.txt` suffixes

Placeholder files had been created on Windows where Explorer appended
`.txt`. Renamed on disk (git mv) and updated in docs:
`CARM.ansa.txt` → `CARM.ansa`,
`Batch_Scenario_carm.ansa.txt` → `Batch_Scenario_carm.ansa`,
`CARM.msh.h5.txt` → `CARM.msh.h5`. Contents unchanged; they remain
placeholders (see REQUISITOS §1 and D08).

Touches: JAMAL_Struct_Folders/01-GRIDS/**, docs/REQUISITOS-REFACTOR-PYTHON.md.
