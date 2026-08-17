# Plan: SQLite `KnownStateHandler` backend (active working plan)

**Status:** locked. Plan is finalized; implementation follows the
"Implementation plan" + "Commit plan" sections below.

**Task:** add a new `KnownStateHandler` implementation backed by a
local SQLite database, alongside the existing four backends (local
JSON / YAML, Azure Blob, AWS S3).

## Goal

Give callers a fifth `KnownStateHandler` backend — a single-file local
SQLite database — that satisfies the existing
`KnownStateHandler` [`Protocol`](../../src/pylibreconcile/known_state/protocol.py)
without adding any new runtime dependencies (Python's `sqlite3`
stdlib module is sufficient).

Concretely:

1. Implement `SQLiteKnownStateHandler` in
   `src/pylibreconcile/known_state/sqlite.py`.
2. Export it from
   [`src/pylibreconcile/known_state/__init__.py`](../../src/pylibreconcile/known_state/__init__.py)
   and the top-level
   [`src/pylibreconcile/__init__.py`](../../src/pylibreconcile/__init__.py)
   so it sits alongside the other handlers in the public API.
3. Add unit tests in `tests/known_state/sqlite_test.py` mirroring the
   coverage of `tests/known_state/local_test.py` and `yaml_test.py`.
4. Update agent-facing context docs
   ([`docs/context/glossary.md`](../../docs/context/glossary.md),
   [`docs/context/overview.md`](../../docs/context/overview.md)) and
   `CHANGELOG.md` so the new backend is discoverable and the current
   state of the world matches reality.

## Existing state (relevant to this plan)

### Protocol

[`src/pylibreconcile/known_state/protocol.py`](../../src/pylibreconcile/known_state/protocol.py)
defines the contract every backend must satisfy. Four methods, all
string-typed:

```python
@runtime_checkable
class KnownStateHandler(Protocol):
    def has_key(self, key: str) -> bool: ...
    def get_all_keys(self) -> list[str]: ...
    def get_value(self, key: str) -> str: ...
    def set_value(self, key: str, value: str) -> None: ...
```

`get_value` raises `KeyError` for missing keys — this is the
contract every existing backend honours and the SQLite one must too.

### Existing backends

Four implementations live in `src/pylibreconcile/known_state/`:

| File | Backend | Storage | Runtime dep | Lock model |
| --- | --- | --- | --- | --- |
| `json_local.py` | `LocalJSONKnownStateHandler` | local JSON file (`Path`) | stdlib + base64 | `threading.Lock` |
| `yaml_local.py` | `LocalYAMLKnownStateHandler` | local YAML file (`Path`) | `pyyaml` | `threading.Lock` |
| `azure.py` | `AzureStorageKnownStateHandler` | Azure Blob container | `azure-core`, `azure-storage-blob` | none (cloud SDK) |
| `aws.py` | `AWSS3KnownStateHandler` | S3 bucket + key/object | `boto3` | none (cloud SDK) |

The two local file handlers (`json_local.py`, `yaml_local.py`) are
the structural twins the new SQLite handler should mirror: same
constructor shape (`__init__(self, path: Path) -> None`), same
thread-safety story (`threading.Lock` guarding every public method),
same `_load` / `_save` internal helpers (we'll repurpose that idea
into a `_connect` + `_ensure_schema` helper for SQLite).

### Encoding on disk

`LocalJSONKnownStateHandler` and `LocalYAMLKnownStateHandler`
base64-encode every value before writing and decode on read
(see
[`src/pylibreconcile/known_state/json_local.py:25`](../../src/pylibreconcile/known_state/json_local.py)
and `yaml_local.py:26`). The reason is purely portability — JSON /
YAML serialisation does not preserve raw binary, and base64 is a
safe container for any UTF-8 string in those formats.

**SQLite stores TEXT natively, including arbitrary UTF-8.** There is
no need to base64-encode. The SQLite handler stores values directly
in a `TEXT` column. This is a deliberate divergence from the local
file handlers, not an oversight, and is called out in the test
plan.

### Public exports

Top-level [`src/pylibreconcile/__init__.py`](../../src/pylibreconcile/__init__.py)
re-exports every `KnownStateHandler` implementation:

```python
from .known_state import (
    AWSS3KnownStateHandler,
    AzureStorageKnownStateHandler,
    KnownStateHandler,
    LocalJSONKnownStateHandler,
    LocalYAMLKnownStateHandler,
)
```

The new handler must be added here so the Sphinx autosummary-driven
[`docs/sphinx/source/api.rst`](../../docs/sphinx/source/api.rst) picks
it up automatically (the `api.rst` file uses `recursive: True`, so
no Sphinx source edits are required).

### Tests

Tests live in `tests/known_state/` and use the standard pytest
`tmp_path` fixture for file-backed backends. Coverage of each
existing backend covers:

- `set_value` + `get_value` round-trip
- `has_key` for present / absent
- `get_all_keys` ordering / contents
- `get_value` raises `KeyError` for missing key
- persistence across instances
- non-existent file is empty (no error)
- overwrite existing value
- special-character / non-ASCII values round-trip cleanly

For SQLite, "non-existent file is empty" translates to "non-existent
DB file is empty after schema bootstrap." See the test plan below.

### Context docs that mention the backend list

The agent-facing context docs hard-code the backend list in three
places that need updating once the SQLite handler lands:

- [`docs/context/overview.md:28-29`](../../docs/context/overview.md)
  — "via `KnownStateHandler` (already implemented with local JSON /
  YAML, Azure Blob, and AWS S3 backends)."
- [`docs/context/overview.md:49`](../../docs/context/overview.md)
  — "from the existing `KnownStateHandler` backends (local JSON /
  YAML / Azure Blob / AWS S3)."
- [`docs/context/overview.md:92-93`](../../docs/context/overview.md)
  — "`KnownStateHandler` — currently a key → string-value store with
  local JSON / YAML / Azure Blob / AWS S3 backends."
- [`docs/context/glossary.md:78-80`](../../docs/context/glossary.md)
  — the `KnownStateHandler` glossary entry.

(There are also three matching occurrences in
[`docs/plans/0002-bootstrap-docs-context.md`](0002-bootstrap-docs-context.md),
but those are inside the historical plan transcript — they describe
the state **at the time the plan was written** and must NOT be
edited, otherwise the plan loses its historical value. The plan file
itself is a historical record, not a current-state doc. This is the
same principle as not editing an old changelog entry.)

### CHANGELOG

[`CHANGELOG.md`](../../CHANGELOG.md) `[Unreleased] > ### Added`
already lists the four existing handlers but **omits
`LocalYAMLKnownStateHandler`** (this is a pre-existing bug noted in
[`docs/plans/0002-bootstrap-docs-context.md:844-846`](0002-bootstrap-docs-context.md)).
The new entry will list all five.

## Locked decisions

These are the design decisions made for this plan. They are recorded
so the implementer does not have to re-derive them.

### D-SQL-1 — Use the Python stdlib `sqlite3` module (no new dependency)

**Decision:** the implementation imports only `sqlite3` (stdlib). No
new entry in `pyproject.toml`'s `[project] dependencies`.

**Rationale:**

- `sqlite3` is in the standard library; Python `>=3.12` (per
  `pyproject.toml`) ships with a recent SQLite version.
- Adds zero dependency weight and zero supply-chain surface.
- The other local handlers already use stdlib (`json`, `pathlib`).
  Following the same convention keeps the local-backend family
  coherent.
- SQLAlchemy (`sqlalchemy` package) was considered and rejected: it
  is a large dependency with its own API surface and is overkill for
  a single-table key/value store. If a future plan needs richer SQL
  (joins, migrations, etc.) we can revisit; for the current
  protocol surface, raw `sqlite3` is the right tool.

### D-SQL-2 — Local file only (no in-memory variant)

**Decision:** the constructor takes a single `path: Path` argument
that points to a file on disk. No `:memory:` support.

**Rationale:**

- Mirrors the existing `LocalJSONKnownStateHandler` /
  `LocalYAMLKnownStateHandler` constructor signature exactly.
  Callers who want in-memory state already have the dict-keyed JSON
  / YAML handlers (a fresh empty file is conceptually the same as
  an empty dict).
- `:memory:` databases are per-connection, so to be useful they'd
  need an "open and hold" semantic that diverges from the existing
  "construct with a path, instance lives forever" pattern.

### D-SQL-3 — Single persistent connection guarded by a `threading.Lock`

**Decision:**

- Open one `sqlite3.Connection` in `__init__`. Hold it for the life
  of the handler instance.
- Configure the connection with `check_same_thread=False` so the
  connection can be used across threads (matching the
  multi-thread-safe intent of `LocalJSONKnownStateHandler` /
  `LocalYAMLKnownStateHandler`).
- Wrap every public method in `threading.Lock()` so writes are
  serialised at the application layer.

**Rationale:**

- The Python `sqlite3` docs explicitly say: *"If `False`, the
  connection may be accessed in multiple threads; write operations
  may need to be serialised by the user to avoid data corruption."*
  We follow that guidance — the `Lock` is the serialisation.
- A single persistent connection avoids per-call connect overhead
  and matches the eager-load pattern of the local JSON / YAML
  handlers.
- The `Lock` mirrors the existing local handlers exactly, so the
  threading story is uniform across all three local backends.

### D-SQL-4 — Schema bootstrapped on `__init__`

**Decision:** the table is created (if missing) in `__init__` via a
`CREATE TABLE IF NOT EXISTS` statement.

**Rationale:**

- Self-healing: passing a path to a non-existent file just works.
  This matches the JSON / YAML behaviour where a missing file is
  treated as empty (see
  [`src/pylibreconcile/known_state/json_local.py:19`](../../src/pylibreconcile/known_state/json_local.py):
  `if not self._path.exists(): return {}`).
- Keeps the public method surface clean — no `init()` /
  `setup()` / `migrate()` to call separately.

### D-SQL-5 — Values stored as raw `TEXT` (no base64)

**Decision:** values are written to and read from a `TEXT` column
verbatim. No base64 encoding.

**Rationale:**

- SQLite `TEXT` columns store arbitrary UTF-8 cleanly. Unlike JSON
  / YAML, there is no escaping / quoting concern.
- A test asserting the raw text round-trips correctly (no encoding
  surprises) replaces the base64-on-disk test the local JSON / YAML
  handlers carry. See test plan below.

### D-SQL-6 — Schema is a single table

```sql
CREATE TABLE IF NOT EXISTS known_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Rationale:**

- One-table schema is the simplest mapping from the protocol's
  flat key/value shape. A separate table per "namespace" would
  imply a richer protocol than we have today. Tracked as future
  work in "Future plan seeds" below.

### D-SQL-7 — `set_value` uses `INSERT OR REPLACE`

**Decision:** `set_value` issues a single
`INSERT OR REPLACE INTO known_state (key, value) VALUES (?, ?)`
statement.

**Rationale:**

- A single SQL statement covers both insert and overwrite paths,
  matching the protocol's "set this value" semantics (no separate
  "create" / "update" methods).
- `INSERT OR REPLACE` is the simplest SQLite idiom for upsert and
  doesn't require the `ON CONFLICT` clause introduced in SQLite
  3.24 (May 2018) — keeping us portable to any Python `>=3.12`
  bundled SQLite.

### D-SQL-8 — Class name `SQLiteKnownStateHandler`, file `sqlite.py` (no `Local` prefix)

**Decision:** the class is `SQLiteKnownStateHandler` and lives in
`src/pylibreconcile/known_state/sqlite.py`. The `Local` prefix
that the early-draft versions of this plan used (i.e.
`LocalSQLiteKnownStateHandler` in `sqlite_local.py`) is dropped.

**Rationale:**

- The four existing backends mix the `Local` prefix for
  *file-on-disk* handlers (`LocalJSONKnownStateHandler`,
  `LocalYAMLKnownStateHandler`) and drop it for *remote / cloud*
  handlers (`AWSS3KnownStateHandler`, `AzureStorageKnownStateHandler`).
  The `Local` prefix is a hint that the handler is "the on-disk
  variant of a protocol that has a remote variant" — but SQLite
  has no remote variant on the project's roadmap, so the
  prefix is misleading rather than informative.
- The file naming follows the same convention: `json_local.py`
  and `yaml_local.py` carry the suffix; `aws.py` and `azure.py`
  do not. `sqlite.py` (no suffix) reflects that there is no
  remote-SQLite variant to disambiguate from.
- The user's review captured this as: *"local has no meaning
  since sqlite is always local and I have no plans to support
  some remote option at this time."*

**Effect on existing prose:** all references in this plan to
`LocalSQLiteKnownStateHandler` and `sqlite_local.py` have been
renamed accordingly. The PR's commit history includes the rename
as a follow-up sequence (`refactor!:`, `test:`, `docs:`) layered
on top of the original five commits.

## Open decisions left to the implementer (no blocker)

The implementer should follow the conventions in
[`AGENTS.md`](../../AGENTS.md) and
[`.opencode/rules/separate-commits.md`](../../.opencode/rules/separate-commits.md).
Specifically:

- Commit `src/` first (`feat:`), then `tests/` (`test:`), then
  `docs/` (`docs:`), then `CHANGELOG.md` (`chore:`). Tooling is
  untouched (no `pyproject.toml` change — stdlib only).
- Public class names should be exactly as specified below.
  Sphinx autosummary will pull them in automatically — no
  `docs/sphinx/source/api.rst` edit needed.
- Use `make all` (`make lint && make format-check && make typecheck &&
  make security && make test`) as the green light, per `AGENTS.md`
  rule 5.

## Implementation plan

### File 1 — `src/pylibreconcile/known_state/sqlite.py` (NEW)

Mirror the structural shape of
[`src/pylibreconcile/known_state/json_local.py`](../../src/pylibreconcile/known_state/json_local.py):

```python
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .protocol import KnownStateHandler


class SQLiteKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by a local SQLite database file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        # check_same_thread=False because we serialise via _lock.
        self._connection = sqlite3.connect(
            self._path, check_same_thread=False
        )
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS known_state ("
            "    key   TEXT PRIMARY KEY,"
            "    value TEXT NOT NULL"
            ")"
        )
        self._connection.commit()

    def has_key(self, key: str) -> bool:
        with self._lock:
            cursor = self._connection.execute(
                "SELECT 1 FROM known_state WHERE key = ?", (key,)
            )
            return cursor.fetchone() is not None

    def get_all_keys(self) -> list[str]:
        with self._lock:
            cursor = self._connection.execute(
                "SELECT key FROM known_state"
            )
            return [row[0] for row in cursor.fetchall()]

    def get_value(self, key: str) -> str:
        with self._lock:
            cursor = self._connection.execute(
                "SELECT value FROM known_state WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(key)
            return row[0]

    def set_value(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO known_state (key, value) "
                "VALUES (?, ?)",
                (key, value),
            )
            self._connection.commit()
```

Notes for the implementer:

- The module docstring is intentionally short; Sphinx autodoc will
  pick up the class docstring.
- `self._path.parent.mkdir(parents=True, exist_ok=True)` is **not**
  called here. SQLite's `connect()` will raise if the parent
  directory doesn't exist — that is fine, and matches what most
  callers expect ("you gave me a path; the directory should
  exist"). If we want auto-mkdir later, that is a separate
  enhancement; see "Future plan seeds" below.
- `check_same_thread=False` plus `threading.Lock` is the
  application-level serialisation strategy. Document this in the
  class docstring so future readers know why the `Lock` is there.
- Parameterised queries (`?` placeholders) — never string-format
  the SQL. The values come from `KnownStateHandler` users and could
  contain anything. (Defence-in-depth even though the protocol
  treats values as opaque strings.)

### File 2 — `src/pylibreconcile/known_state/__init__.py` (EDIT)

Add the import and the `__all__` entry:

```diff
 from .aws import AWSS3KnownStateHandler
 from .azure import AzureStorageKnownStateHandler
+from .sqlite import SQLiteKnownStateHandler
 from .json_local import LocalJSONKnownStateHandler
 from .protocol import KnownStateHandler
 from .yaml_local import LocalYAMLKnownStateHandler

 __all__ = [
     "AWSS3KnownStateHandler",
     "AzureStorageKnownStateHandler",
+    "SQLiteKnownStateHandler",
     "KnownStateHandler",
     "LocalJSONKnownStateHandler",
     "LocalYAMLKnownStateHandler",
 ]
```

(Imports grouped to match isort's `combine-as-imports` config in
`pyproject.toml`. The exact ordering above matches what `ruff format`
will produce — implementer should run `make format` to settle it.)

### File 3 — `src/pylibreconcile/__init__.py` (EDIT)

Add the re-export and `__all__` entry to keep the top-level public
API consistent with the existing four handlers:

```diff
 from .core import DesiredState
 from .known_state import (
     AWSS3KnownStateHandler,
     AzureStorageKnownStateHandler,
+    SQLiteKnownStateHandler,
     KnownStateHandler,
     LocalJSONKnownStateHandler,
     LocalYAMLKnownStateHandler,
 )
 from .reconciler import Reconciler

 __all__ = [
     "AWSS3KnownStateHandler",
     "AzureStorageKnownStateHandler",
     "DesiredState",
+    "SQLiteKnownStateHandler",
     "KnownStateHandler",
     "LocalJSONKnownStateHandler",
     "LocalYAMLKnownStateHandler",
     "Reconciler",
 ]
```

### File 4 — `tests/known_state/sqlite_test.py` (NEW)

Mirror `tests/known_state/local_test.py` line for line, with the
following substitutions to reflect the SQLite divergence:

- Constructor: `SQLiteKnownStateHandler(tmp_path / "state.db")`
  — file extension `.db` to match SQLite convention; the underlying
  SQLite engine treats any extension identically, this is purely a
  readability choice.
- The `test_values_are_base64_encoded_on_disk` test from
  `local_test.py` does NOT apply (we are NOT base64-encoding).
  Replace with a test that the raw value is stored verbatim —
  either by inspecting the on-disk row via a second connection, or
  by reading the file content and asserting the value appears
  unmodified. (Recommended: open a second
  `sqlite3.connect(path)` and read the value back.)
- The `test_non_dict_json_is_empty` test does NOT apply — SQLite
  has no equivalent of a malformed top-level structure because we
  own the schema. Replace with a `test_schema_is_created_on_init`
  test that asserts the table exists after construction.
- Add a `test_concurrent_writes_do_not_corrupt` test using
  `threading.Thread` + `concurrent.futures.ThreadPoolExecutor` to
  exercise the `Lock` and confirm no `sqlite3.OperationalError`
  ("database is locked") leaks out. This is the SQLite-specific
  thread-safety smoke test the local JSON / YAML handlers do not
  need because their lock model is purely in-process (no underlying
  file lock to race against).

The full test list:

| Test | What it covers |
| --- | --- |
| `test_set_and_get_value` | round-trip set → get |
| `test_has_key` | present + absent |
| `test_get_all_keys` | multi-key insertion, ordering, content |
| `test_get_missing_key_raises` | `KeyError` contract |
| `test_persists_across_instances` | new `SQLiteKnownStateHandler(path)` reads what the previous instance wrote |
| `test_nonexistent_file_is_empty` | `get_all_keys() == []`, `has_key(any)` is False after init on a fresh path |
| `test_schema_is_created_on_init` | introspect via `sqlite_master` — `known_state` table exists with `key TEXT PRIMARY KEY, value TEXT NOT NULL` |
| `test_values_stored_verbatim` | writes `"hello\nworld\twith\0chars"`, reads it back unchanged, and asserts the on-disk row is the raw string (not base64-encoded) |
| `test_overwrite_existing_value` | second `set_value` for the same key replaces |
| `test_concurrent_writes_do_not_corrupt` | `ThreadPoolExecutor` with `set_value` from many threads; asserts final state matches expected count and no exception surfaces |

### File 5 — `tests/known_state/protocol_test.py` (EDIT, optional)

Extend `test_cloud_handlers_are_subclasses` (or add a sibling test)
to assert `SQLiteKnownStateHandler` is a subclass of
`KnownStateHandler`. This is purely a structural check; the runtime
protocol test (`isinstance(handler, KnownStateHandler)`) will also
exercise it transitively. Recommend the sibling-test form to keep
the existing test untouched.

### File 6 — `docs/context/glossary.md` (EDIT)

In the `KnownStateHandler` glossary entry (lines 78-80), update the
backend list:

```diff
-- **KnownStateHandler** — the Protocol that backs Known State
-  persistence. Already implemented with local JSON / YAML / Azure
-  Blob / AWS S3 backends.
+- **KnownStateHandler** — the Protocol that backs Known State
+  persistence. Already implemented with local JSON / YAML / SQLite
+  / Azure Blob / AWS S3 backends.
```

### File 7 — `docs/context/overview.md` (EDIT)

Three places list the existing backends. All three need updating:

- Lines 28-29 — "via `KnownStateHandler` (already implemented with
  local JSON / YAML, Azure Blob, and AWS S3 backends)."
- Line 49 — "from the existing `KnownStateHandler` backends (local
  JSON / YAML / Azure Blob / AWS S3)."
- Lines 92-93 — "`KnownStateHandler` — currently a key → string-value
  store with local JSON / YAML / Azure Blob / AWS S3 backends."

Each becomes "local JSON / YAML / SQLite / Azure Blob / AWS S3."

### File 8 — `CHANGELOG.md` (EDIT)

Under `[Unreleased] > ### Added`, expand the existing bullet and fix
the pre-existing YAML omission:

```diff
 ### Added

-- `KnownStateHandler` protocol and its implementations:
-  `LocalJSONKnownStateHandler`, `AzureStorageKnownStateHandler`, and
-  `AWSS3KnownStateHandler`.
+- `KnownStateHandler` protocol and its implementations:
+  `LocalJSONKnownStateHandler`, `LocalYAMLKnownStateHandler`,
+  `SQLiteKnownStateHandler`,
+  `AzureStorageKnownStateHandler`, and `AWSS3KnownStateHandler`.
```

(The YAML addition is a pre-existing
[`CHANGELOG.md`](../../CHANGELOG.md) gap noted in
[`docs/plans/0002-bootstrap-docs-context.md:844-846`](0002-bootstrap-docs-context.md).
Bundling it into the same commit is acceptable here because it is
the same category of change ("documentation accuracy for an existing
implementation") and avoids a follow-up chore commit. If the user
prefers a strictly-scoped commit, split it out — see "Commit plan"
below for the two options.)

## Files NOT changed in this plan

- `src/pylibreconcile/known_state/protocol.py` — the Protocol stays
  the same; SQLite is just another implementation.
- `src/pylibreconcile/known_state/json_local.py`,
  `yaml_local.py`, `azure.py`, `aws.py` — untouched.
- `docs/sphinx/source/api.rst` — uses `recursive: True` autosummary,
  picks up the new class automatically.
- `pyproject.toml` — no new dependency.
- `Makefile` — no new target.
- `uv.lock` — unchanged (no new dep).
- `docs/plans/0002-bootstrap-docs-context.md` — historical plan
  transcript. Do NOT edit. Its backend-list mentions are a
  snapshot of state at plan-write time.
- `.gitignore` — no new patterns. SQLite files (`.db`, `.sqlite`,
  `.sqlite3`) created in tests live in pytest's `tmp_path`, which is
  out-of-tree and not committed.

## Commit plan (per `.opencode/rules/separate-commits.md`)

Per `AGENTS.md` rule 11 and
[`.opencode/rules/separate-commits.md`](../../.opencode/rules/separate-commits.md):

**Pre-step — finalize the plan file.** Before any of the
implementation commits below, the `PLAN.md` → numbered-rename
specified under "Plan file lifecycle" must land as its own commit:

```bash
git mv docs/plans/PLAN.md docs/plans/0004-sqlite-known-state-handler.md
# also flip the Status: line at the top from "drafting" to "locked"
git commit -m "chore(plan): finalize plan as 0004-sqlite-known-state-handler"
```

This commit is the precondition for the four implementation commits
below — once it lands, every subsequent commit references the
renamed plan path.

**Option A — strictly-scoped (preferred):**

1. `feat: add SQLiteKnownStateHandler` — `src/pylibreconcile/known_state/sqlite.py`,
   `src/pylibreconcile/known_state/__init__.py`, `src/pylibreconcile/__init__.py`.
2. `test: cover SQLiteKnownStateHandler` — `tests/known_state/sqlite_test.py`,
   `tests/known_state/protocol_test.py` (sibling test).
3. `docs: mention SQLite KnownStateHandler backend in context` —
   `docs/context/glossary.md`, `docs/context/overview.md`.
4. `chore: update CHANGELOG for SQLite KnownStateHandler` —
   `CHANGELOG.md` (with the YAML fix-up bundled in).

**Option B — merge CHANGELOG into docs:**

If the user prefers fewer commits, merge commit 4 into commit 3
(one `docs:` commit covering all `.md` changes including
`CHANGELOG.md`). Either is acceptable per the rule; the rule
forbids mixing source/tests together but does not strictly separate
`CHANGELOG.md` from other docs.

**Follow-up — naming cleanup (D-SQL-8).** After the four
implementation commits above land, three rename commits are
layered on top so the class ends up as `SQLiteKnownStateHandler`
in `sqlite.py` rather than `LocalSQLiteKnownStateHandler` in
`sqlite_local.py` (see D-SQL-8 for the rationale):

1. `refactor!: rename LocalSQLiteKnownStateHandler to SQLiteKnownStateHandler` —
   `src/pylibreconcile/known_state/sqlite.py` (was `sqlite_local.py`),
   `src/pylibreconcile/known_state/__init__.py`,
   `src/pylibreconcile/__init__.py`. Intermediate tree state: tests
   still import the old name and will fail until the next commit.
2. `test: rename to SQLiteKnownStateHandler` —
   `tests/known_state/sqlite_test.py`,
   `tests/known_state/protocol_test.py`. After this commit the tree
   is fully green again.
3. `docs: rename to SQLiteKnownStateHandler in CHANGELOG and plan` —
   `CHANGELOG.md` and the locked plan itself. Sphinx pages will
   re-render with the new class name on the next docs build.

The rename is split across three commits so each commit touches
exactly one layer (`src/` / `tests/` / `docs`+`CHANGELOG`+plan),
preserving the project's separate-commits rule. The intermediate
`refactor!:` commit will fail `make test-fast` until commit 2
lands — that is the documented cost of layer-splitting a
coordinated rename.

## Validation sequence

After implementation:

1. `make install` — confirm sync still works (no new dep, but worth
   confirming lockfile is untouched).
2. `make lint` — `ruff check` must pass on the new module and
   edited files.
3. `make format` then `make format-check` — formatting must round-trip.
4. `make typecheck` — strict `mypy` must pass. `sqlite3` is in the
   stdlib; types are `sqlite3.Connection`, `sqlite3.Cursor`,
   `Path`, `str`, `bool`, `None`. All standard.
5. `make security` — `bandit` must pass. The new module's only
   "interesting" call is `sqlite3.connect(path)` with a
   `pathlib.Path` argument; bandit has no rules that should fire.
   `pip-audit` will pass trivially (no new dep).
6. `make test` — full coverage run. Target: 100% branch coverage
   on the new module, matching the rest of the project
   (`tool.coverage` already runs with `branch = true`).
7. `make docs` — Sphinx build should pick up the new class via
   autosummary and emit an `SQLiteKnownStateHandler` page.
8. `make all` — final green light.

## Open questions

None at draft time. All design decisions are recorded under
"Locked decisions" above. The implementer can proceed.

## What this plan does NOT include

- Adding any new third-party dependency (e.g. SQLAlchemy).
- Changing the `KnownStateHandler` Protocol itself.
- Any other backend (Postgres, MySQL, Redis, MongoDB, etc.).
- Concurrent multi-process access (the `threading.Lock` is
  in-process; cross-process serialisation requires a different
  model — see Future plan seeds below).
- Any change to the Reconciler / DesiredState code path. The new
  handler is a drop-in replacement that conforms to the existing
  protocol.

## Future plan seeds

These notes are kept here so a future planner does not have to
re-derive them. They are **not** part of this plan.

### Seed SQL-1 — Multi-process / cross-process safety

The current design serialises within a single process. SQLite
itself supports multi-process access via file locks and the
`?mode=ro?` / `?mode=rw?` URI schemes, but the Python stdlib
`sqlite3.connect()` does not expose SQLite's WAL mode or busy
timeout tuning beyond the `timeout=` constructor argument (default
5.0s — see the stdlib docs cited in D-SQL-3). If a future plan
needs cross-process safety (e.g. multiple `Reconciler` instances
sharing one DB), the relevant knobs are `journal_mode=WAL`,
`synchronous=NORMAL`, and a non-default `timeout`.

### Seed SQL-2 — Auto-create parent directory

`LocalJSONKnownStateHandler` and `LocalYAMLKnownStateHandler` call
`self._path.parent.mkdir(parents=True, exist_ok=True)` before
writing (see
[`src/pylibreconcile/known_state/json_local.py:32`](../../src/pylibreconcile/known_state/json_local.py)).
The SQLite handler does not. If callers complain about having to
`mkdir` first, a one-line fix is to add the same call to
`__init__`. Held back here to keep SQLite semantics closer to
"the path you passed must exist" — matches user mental model of
"this is a database file, I want to control where it lives."

### Seed SQL-3 — Namespacing / per-resource tables

A single global `known_state` table is fine for the current flat
protocol. If a future expansion (Seed 2 in
[`docs/plans/0002-bootstrap-docs-context.md`](0002-bootstrap-docs-context.md))
adds richer Known State values, a per-`DesiredState`-type or
per-namespace table layout may make sense. Defer until the
protocol grows.

### Seed SQL-4 — `deserialize` / `serialize` round-trip hook

The local JSON / YAML handlers' base64-on-disk behaviour is a
poor-man's "any string is safe to round-trip" guarantee. SQLite
needs no such trick (TEXT is byte-clean). But if a future Known
State value type is more than a string (per Seed SQL-3 above), the
SQLite handler will need a serialize/deserialize hook analogous to
SQLite's `detect_types` parameter. Defer.

## Plan file lifecycle

Before this plan moves into implementation, the active working file
at `docs/plans/PLAN.md` must be renamed to follow the project's
numbered-prefix convention used by
[`0001-context-folder-bootstrap.md`](0001-context-folder-bootstrap.md)
and
[`0002-bootstrap-docs-context.md`](0002-bootstrap-docs-context.md):

```bash
git mv docs/plans/PLAN.md docs/plans/0004-sqlite-known-state-handler.md
```

**Why `0004` and not `0003`.** The numbering slot `0003` is
already claimed by an in-flight plan in another worktree (running
agent on a sibling branch). This plan takes the next free slot,
`0004`. This avoids a rename collision if both plans eventually
land in the same branch / merge.

**Why this filename.** `0004-sqlite-known-state-handler.md` is
kebab-case, descriptive of the work, and matches the pattern of
the existing two plan files (`<scope>-<target>-<action-or-topic>`).

**Commit it as its own commit**, separate from the code / test /
doc / changelog commits specified under "Commit plan":

```bash
git commit -m "chore(plan): finalize plan as 0004-sqlite-known-state-handler"
```

After the rename, flip the `Status:` line at the top of the file
from `drafting` to `locked` so the file signals it is ready for
implementation. (The header title `"Plan: SQLite ..."` and the
`## Goal` block stay verbatim — they describe the work, not the
file lifecycle.)

The cross-references in the body of the renamed file (`../../src/...`,
`../../docs/...`, etc.) are relative paths and resolve correctly
from the new location — no edits required.

## Next step (when implementation starts)

The `code-worker` should:

1. Implement `src/pylibreconcile/known_state/sqlite.py` per
   the "File 1" spec above.
2. Wire up the two `__init__.py` re-exports per "File 2" / "File 3".
3. Add `tests/known_state/sqlite_test.py` per "File 4".
4. Optionally extend `tests/known_state/protocol_test.py` per
   "File 5".
5. Update `docs/context/glossary.md` and
   `docs/context/overview.md` per "File 6" / "File 7".
6. Update `CHANGELOG.md` per "File 8".
7. Land commits in the order specified under "Commit plan".
8. Run `make all` for green light, then hand off to the user.
