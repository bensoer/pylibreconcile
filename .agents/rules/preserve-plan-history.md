# Preserve Plan History

**Rule:** Do not edit already-executed plan files in `docs/plans/`. Once a
plan has been implemented and committed, its file is a historical record —
read-only. Closing seeds, updating status lines, or retroactively documenting
resolution in an older plan corrupts history.

**Where status updates go:**
- The new plan file itself (e.g. `docs/plans/0004-wiring-container.md`)
  is the authoritative record of what it resolves.
- If a seed references an older plan's open item, the new plan's body or
  header documents the resolution. Do not touch the old file.

**Applicable files:** `docs/plans/0*` and any file under `docs/plans/` that
preexists the current work.