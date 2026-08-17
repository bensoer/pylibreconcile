# Plan: Add a `BoltDBKnownStateHandler` (KnownState boltdb backend)

**Status:** drafting — ready for review. This plan adds a new
`KnownStateHandler` implementation backed by [boltdb][pypi-boltdb], a pure
Python port of the Bolt/bbolt embedded key/value store. The four existing
handlers (`LocalJSONKnownStateHandler`, `LocalYAMLKnownStateHandler`,
`AzureStorageKnownStateHandler`, `AWSS3KnownStateHandler`) cover file and
cloud blob stores; this adds an embedded transactional store for users who
want bbolt-style ACID semantics and byte-sorted key iteration without
running a separate server.

[pypi-boltdb]: https://pypi.org/project/boltdb/

## Goal

Add a new `BoltDBKnownStateHandler` class in
`src/pylibreconcile/known_state/boltdb.py` that satisfies the existing
`KnownStateHandler` protocol and exposes the same four-method surface
(`has_key`, `get_all_keys`, `get_value`, `set_value`) the other handlers
do. Export it from the `pylibreconcile/known_state/__init__.py` and the
top-level `pylibreconcile/__init__.py`, document it in the changelog,
and cover it with tests in `tests/known_state/boltdb_test.py`.

## Background

### Why boltdb?

The library already supports four backends for Known State:

- **`LocalJSONKnownStateHandler`** (`src/pylibreconcile/known_state/json_local.py:11`)
  — local JSON file, base64-encoded values, single-process locking via
  `threading.Lock`. Reloads the entire file on every write. Good for
  small state, single-process scripts, no extra deps.
- **`LocalYAMLKnownStateHandler`** (`src/pylibreconcile/known_state/yaml_local.py:12`)
  — same shape as JSON, YAML serialization.
- **`AzureStorageKnownStateHandler`** (`src/pylibreconcile/known_state/azure.py:9`)
  — Azure Blob Storage. Network round-trip per call.
- **`AWSS3KnownStateHandler`** (`src/pylibreconcile/known_state/aws.py:11`)
  — AWS S3. Network round-trip per call.

`boltdb` is an embedded, transactional, B+tree-backed KV store. It
gives us:

- ACID semantics for free (single-writer, multi-reader transactions).
- Byte-sorted keys (relevant if we ever do prefix scans — currently
  not used by the protocol but worth keeping the door open).
- A mmap'd single-file store that's significantly faster than the
  JSON/YAML handlers for large state (which reload the entire file on
  every write via `_load`).
- Local-only, no server to run.

This slots in next to the two local handlers as another "local,
single-machine" option, but with much better write throughput for
non-trivial state sizes.

### Constraints of the chosen `boltdb` package

The PyPI package `boltdb` (v0.0.2, last release 2020-10-06) is the
only actively-importable Python port of Bolt available today. We have
**verified** its surface by reading the source on GitHub:

- **Linux-only.** It uses `fcntl.lockf()` for file locking (see
  `boltdb/db.py:7,17-21`). macOS and Windows are not supported by the
  package itself. We will document this as a platform constraint.
- **Single-process writer.** Per bbolt semantics: one process can hold
  a writable transaction at a time. Multiple readers are fine. Matches
  bbolt's documented behaviour — see
  [etcd-io/bbolt README](https://github.com/etcd-io/bbolt).
- **API surface** (per `boltdb/db.py`, `boltdb/bucket.py`,
  `boltdb/tx.py`):
  - `BoltDB(filename, readonly=False)` — opens or creates the file.
    The DB object holds the underlying mmap and lock; per the source,
    `__del__` calls `close()`. We will hold the `BoltDB` instance in
    our handler and ensure `close()` is callable.
  - `db.update()` / `db.view()` — context managers yielding a `Tx`.
  - `tx.bucket(name=None)` — returns root bucket by default; pass a
    name to get a sub-bucket. The first level of nested buckets is
    supported.
  - `tx.create_bucket(name)` — must be called inside a writable tx.
  - `bucket.put(key, value)` / `bucket.get(key)` /
    `bucket.delete(key)` / `bucket.cursor()` — KV ops.
  - `Cursor` yields `(key, value)` via iteration, supports `first()` /
    `seek(key)` / `next()`. We use iteration to enumerate all keys.

The `boltdb` package **has no real test suite on PyPI** to lean on
(only the author's `tests/test_bucket.py` example). Behaviour we
verify in our own tests is the contract we ship against — see the
test list below.

### Why not just use SQLite via `sqlite3` or `sqlitedict`?

The user asked for boltdb specifically. SQLite would be a different
backend (and would belong in a separate plan / PR). If the user
later wants SQLite, it can be added then — they are not equivalent
stores even though both are embedded KVs.

## Locked decisions

1. **Use the PyPI package `boltdb>=0.0.2`.** Add it to
   `pyproject.toml [project].dependencies`. We do not vendor a fork
   and we do not use lmdb / plyvel / sqlitedict — those would be
   different decisions and the user asked for boltdb.
2. **Filename-based handler, single bucket.** Construct with
   `BoltDBKnownStateHandler(path, *, bucket_name: str = "known_state")`.
   All keys/values live inside one named bucket (default
   `known_state`) on a per-file `BoltDB` store. Mirrors how the local
   handlers take a `path`. Multi-handler-per-file is a future-plan
   surface, not V1.
3. **Bucket is created on first open.** Constructor runs `update()`
   to call `create_bucket_if_missing` (we will use the safer
   `tx.bucket(name)` + create-if-missing pattern) so the handler is
   usable immediately. Failures (corrupt file, locked by another
   process) propagate to the caller — no swallowed exceptions.
4. **Plain UTF-8 strings for keys and values.** Matches the existing
   protocol signature (`key: str`, `value: str`). No base64 dance —
   the boltdb `Bucket.put`/`Bucket.get` accept `bytes`, so we
   `.encode("utf-8")` on the way in and `.decode("utf-8")` on the
   way out. This is simpler than the JSON/YAML handlers' base64
   trick and consistent with how the cloud handlers treat values
   (raw text — see `aws.py:39` decoding bytes via utf-8).
5. **No internal `threading.Lock`.** boltdb serializes writers at
   the file-lock level (one writer at a time) and supports multiple
   readers via its own RW lock. Adding a Python-level lock on top
   would just deadlock. The handler is thread-safe in the same
   sense bbolt is — concurrent readers are fine, concurrent writers
   serialize.
6. **`close()` is exposed but optional.** The boltdb `BoltDB` object
   holds an OS file lock; leaving the file open means another
   process can't open it for writing. We add a `close()` method on
   `BoltDBKnownStateHandler` that forwards to the underlying
   `BoltDB.close()`, and rely on `__del__` as a safety net (matching
   the boltdb package's own behaviour). Users who care about prompt
   lock release can call `close()` explicitly; users who don't
   (typical script / one-shot reconcile usage) get the implicit
   cleanup. We do NOT make the handler a context manager in V1 —
   adding `__enter__`/`__exit__` later is non-breaking.
7. **Platform marker: Linux only.** Document this in the docstring
   and in the changelog. macOS / Windows users will get an
   `ImportError`/`AttributeError` from the underlying `fcntl` import
   at handler construction time. We do not paper over this; we
   surface it.
8. **No lock-file regression tests on the macOS / Windows CI paths.**
   Our project currently runs on Linux CI (`.github/workflows/ci.yml`
   uses `ubuntu-latest` per AGENTS.md context); we do not need to
   add a CI matrix for this handler.
9. **Separate commits per `.opencode/rules/separate-commits.md`** —
   one commit for `src/`, one for `tests/`, one for `docs/` (the
   docs in this case is `CHANGELOG.md`). Tooling changes
   (`pyproject.toml`, `uv.lock`) get their own `build:` / `chore:`
   commits. See "Commit plan" below.

## Design

### Class shape

```python
# src/pylibreconcile/known_state/boltdb.py
from __future__ import annotations

from pathlib import Path

from boltdb import BoltDB

from .protocol import KnownStateHandler

_DEFAULT_BUCKET = "known_state"


class BoltDBKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by an embedded boltdb file.

    Platform: Linux only. The PyPI ``boltdb`` package uses
    ``fcntl.lockf`` for file locking; macOS and Windows are not
    supported by the upstream package.

    The handler stores all keys in a single named bucket inside the
    file. Concurrent readers are supported by boltdb; only one writer
    at a time (per-process file lock). The handler itself is
    thread-safe in the same sense.
    """

    def __init__(
        self,
        path: Path,
        *,
        bucket_name: str = _DEFAULT_BUCKET,
    ) -> None:
        self._path = path
        self._bucket_name = bucket_name
        self._db = BoltDB(str(path))
        # Ensure the bucket exists.
        with self._db.update() as tx:
            tx.create_bucket(bucket_name)

    def has_key(self, key: str) -> bool:
        with self._db.view() as tx:
            bucket = tx.bucket(self._bucket_name)
            return bucket.get(key.encode("utf-8")) is not None

    def get_all_keys(self) -> list[str]:
        keys: list[str] = []
        with self._db.view() as tx:
            bucket = tx.bucket(self._bucket_name)
            for raw_key, _ in bucket:
                keys.append(raw_key.decode("utf-8"))
        return keys

    def get_value(self, key: str) -> str:
        with self._db.view() as tx:
            bucket = tx.bucket(self._bucket_name)
            raw = bucket.get(key.encode("utf-8"))
        if raw is None:
            raise KeyError(key)
        return raw.decode("utf-8")

    def set_value(self, key: str, value: str) -> None:
        with self._db.update() as tx:
            bucket = tx.bucket(self._bucket_name)
            bucket.put(key.encode("utf-8"), value.encode("utf-8"))

    def close(self) -> None:
        self._db.close()
```

### Mapping the protocol to boltdb

| Protocol method | boltdb operation                                    |
| --------------- | --------------------------------------------------- |
| `has_key`       | `view()` + `bucket.get(encoded)` non-None check     |
| `get_all_keys`  | `view()` + iterate the bucket, decode each key      |
| `get_value`     | `view()` + `bucket.get(encoded)` + `KeyError` if `None` |
| `set_value`     | `update()` + `bucket.put(encoded_key, encoded_value)` |

The single-writer / multi-reader pattern in boltdb maps naturally to
"the reconciler is one process, the known state is one file." For
our use case (one reconciler process reading/writing one state
file), this is correct.

### Why no internal `threading.Lock`

The existing `LocalJSONKnownStateHandler` uses a `threading.Lock`
because the file-level "reload everything, modify, write everything"
cycle is not safe under concurrent writes within the same process —
two threads could both load `{k: v}`, both modify, and the second
write would clobber the first. The boltdb handler does not need
that: the underlying boltdb `update()` context manager serializes
concurrent writers at the boltdb-internal lock level (and will raise
if there is contention on the OS file lock). Adding our own
`threading.Lock` would be redundant and would serialize concurrent
reads unnecessarily.

### Constructor failure modes

- **Permission denied / bad path.** `BoltDB(filename)` raises
  `OSError` / `PermissionError`. Propagates to caller. No special
  handling.
- **Corrupt file.** `BoltDB(filename)` would raise on read. Same as
  above — propagate.
- **File already locked by another process.** `BoltDB(filename)` uses
  `fcntl.lockf(LOCK_EX)` blocking. The lock blocks indefinitely
  unless the upstream package supports a timeout — the source on
  GitHub shows it does not (no `timeout` option). Documented
  limitation: boltdb will hang on open if another process holds the
  lock. This is bbolt's documented behaviour — not a bug we can fix
  from the handler layer. Document in the docstring.

### Test strategy

`tests/known_state/boltdb_test.py` mirrors the structure of
`tests/known_state/local_test.py` and `yaml_test.py`:

- `test_set_and_get_value` — round-trip a value.
- `test_has_key` — pre/post set.
- `test_get_all_keys` — multiple keys, return order independent
  (use `sorted` for assertion since boltdb returns byte-sorted
  ordering — but assert against a sorted list so we don't bake that
  in).
- `test_get_missing_key_raises` — `KeyError`.
- `test_persists_across_instances` — open, set, reopen, read.
- `test_nonexistent_file_is_empty` — handler on a missing file works
  (boltdb creates it).
- `test_overwrite_existing_value` — set twice, last wins.
- `test_unicode_keys_and_values` — non-ASCII strings round-trip.
- `test_close_releases_lock` — after `close()`, a fresh handler on
  the same path can open without hanging. (Smoke test — boltdb will
  block on the lock otherwise.)
- `test_satisfies_protocol` — `isinstance(handler, KnownStateHandler)`.
- `test_default_bucket_name` — the handler uses `known_state` by
  default (we read it back; can't introspect the DB directly, so
  this test is implicit in the others).

No mocking needed — boltdb's whole point is that it's a real file.
Tests use `tmp_path` (matches existing patterns in `local_test.py`).

### Coverage target

`pyproject.toml` already enforces coverage on `src/` (branch +
line). The handler is small enough that 100% is realistic; aim for
it. The existing `__init__.py` files are excluded from coverage
(`pyproject.toml:89`), so the `__init__.py` re-export doesn't need
its own test.

### Dependencies

Add `boltdb>=0.0.2` to `[project].dependencies` in
`pyproject.toml` (not `[dependency-groups] dev` — this is a runtime
dependency like the existing `azure-storage-blob`, `boto3`, `pyyaml`
entries at `pyproject.toml:23-28`).

```diff
 dependencies = [
     "azure-core>=1.41.0",
     "azure-storage-blob>=12.30.0",
     "boto3>=1.43.72",
+    "boltdb>=0.0.2",
     "pyyaml>=6.0.3",
 ]
```

The `boltdb` package is Linux-only (per upstream). macOS / Windows
imports will fail at construction time. Documented above and in the
handler docstring.

### Documentation updates

- **`CHANGELOG.md`** — under `[Unreleased] / Added`, add a bullet
  for `BoltDBKnownStateHandler`. Match the existing style of the
  `LocalJSONKnownStateHandler` / `AzureStorageKnownStateHandler` /
  `AWSS3KnownStateHandler` bullet at `CHANGELOG.md:12-14` (which
  already drops `LocalYAMLKnownStateHandler` — a separate fix that
  should be folded in opportunistically *if* the user wants the
  changelog kept tidy, but is not strictly part of this plan; see
  "Pre-flight observations" in the existing plan at
  `docs/plans/0002-bootstrap-docs-context.md:838-855`).
- **`docs/context/glossary.md`** — no change. The glossary already
  says KnownStateHandler is "implemented with local JSON / YAML /
  Azure Blob / AWS S3 backends" (`docs/context/glossary.md:78-80`).
  Add boltdb to that list when the next context-doc revision happens
  — it's a one-line edit and we don't want to gate this PR on it.
  Flag as a follow-up.
- **`docs/context/overview.md`** — same. The phrase "local JSON /
  YAML, Azure Blob, and AWS S3 backends" appears at
  `docs/context/overview.md:28-29` and again at
  `docs/context/overview.md:50-51`. Adding boltdb there is a
  follow-up, not a blocker.
- **Sphinx docs** — autosummary at `docs/sphinx/source/api.rst`
  picks up new exports automatically via
  `sphinx.ext.autosummary` + recursive. No RST edits needed.

## Implementation sequence

1. **`build:` commit** — `pyproject.toml` add `boltdb>=0.0.2`,
   then `make lock` to refresh `uv.lock`, then commit both files.
2. **`feat:` commit** — add `src/pylibreconcile/known_state/boltdb.py`,
   add the re-export in `src/pylibreconcile/known_state/__init__.py`,
   and add the re-export + `__all__` entry in
   `src/pylibreconcile/__init__.py`.
3. **`test:` commit** — add `tests/known_state/boltdb_test.py`,
   extend `tests/known_state/protocol_test.py` with a
   `test_boltdb_handler_is_instance_of_protocol` (mirrors the
   existing `test_local_handler_is_instance_of_protocol` at
   `protocol_test.py:13`).
4. **`docs:` commit** — `CHANGELOG.md` updated under
   `[Unreleased] / Added`.

Then run `make all` to verify lint, format-check, typecheck,
security, and tests all pass. (pre-commit will run automatically on
each commit.)

## Commit plan (per `.opencode/rules/separate-commits.md`)

Four commits, each with a Conventional Commits prefix:

1. `build: add boltdb runtime dependency`
   - Files: `pyproject.toml`, `uv.lock`.
2. `feat(known-state): add BoltDBKnownStateHandler`
   - Files: `src/pylibreconcile/known_state/boltdb.py`,
     `src/pylibreconcile/known_state/__init__.py`,
     `src/pylibreconcile/__init__.py`.
3. `test(known-state): cover BoltDBKnownStateHandler`
   - Files: `tests/known_state/boltdb_test.py`,
     `tests/known_state/protocol_test.py`.
4. `docs(changelog): note new BoltDBKnownStateHandler`
   - Files: `CHANGELOG.md`.

This is the `src/` / `tests/` / `docs` / tooling split the project
requires.

## Files changed

- `pyproject.toml` — add `boltdb>=0.0.2` to `dependencies`.
- `uv.lock` — refreshed by `make lock` after the `pyproject.toml`
  change.
- `src/pylibreconcile/known_state/boltdb.py` — **new**.
- `src/pylibreconcile/known_state/__init__.py` — add
  `from .boltdb import BoltDBKnownStateHandler` and corresponding
  `__all__` entry.
- `src/pylibreconcile/__init__.py` — add
  `BoltDBKnownStateHandler` import and `__all__` entry.
- `tests/known_state/boltdb_test.py` — **new**.
- `tests/known_state/protocol_test.py` — add a test asserting
  `isinstance(BoltDBKnownStateHandler(...), KnownStateHandler)`
  (mirrors `test_cloud_handlers_are_subclasses` at
  `protocol_test.py:49-54`).
- `CHANGELOG.md` — bullet under `[Unreleased] / Added`.

## Risks and edge cases

- **Linux-only.** Surfaces at import time of `boltdb` itself
  (no `fcntl` on Windows). Documented.
- **Single-writer.** Opening the same file from two processes with
  the second one trying to write will hang on the file lock. This is
  bbolt semantics, not a bug. Documented in the docstring.
- **Close-during-use.** A user could call `close()` then keep
  calling methods; boltdb's underlying `mmap` would fail. We don't
  defensively guard against this — the handler is a thin adapter,
  and an explicit `close()` is the user's signal that they're
  done. (Same trade-off as `LocalJSONKnownStateHandler`, which
  holds an open file handle.)
- **`boltdb` upstream is stale (last release 2020-10-06, 0.0.2).**
  No new versions since. We pin `>=0.0.2` per the plan above; if
  the user wants a tighter pin or wants to vendor / fork, that is a
  separate decision and a separate plan. Flagged under "Open
  questions" below.
- **`boltdb` does not advertise Python 3.13 support explicitly.** The
  setup.py declares `python_requires='>=3.6'` (no upper bound). Our
  `pyproject.toml` declares `requires-python = ">=3.12"` and lists
  Python 3.12 and 3.13 in classifiers (`pyproject.toml:6,18-21`).
  boltdb's pure-Python implementation has no obvious blockers on
  3.12/3.13 — its deps are stdlib only (`os`, `fcntl`, `mmap`,
  `threading`, `contextlib`). Will be confirmed in CI on first
  build; if 3.13 breaks, fall back is to add
  `boltdb>=0.0.2; python_version < "3.13"` — but we don't pre-empt
  that here.

## Pre-flight observations (out of scope for this plan)

- **`CHANGELOG.md` still drops `LocalYAMLKnownStateHandler`** from
  the bullet at `CHANGELOG.md:12-14`. Same observation already
  recorded at
  `docs/plans/0002-bootstrap-docs-context.md:843-846`. The new
  `BoltDBKnownStateHandler` bullet should follow the corrected
  pattern: list all four other backends including YAML. Worth doing
  in this PR if it doesn't muddy the diff (it's one line in the
  bullet). Left as a judgement call for the implementer.
- **`docs/context/glossary.md` and `overview.md`** still list "local
  JSON / YAML / Azure Blob / AWS S3" without boltdb. A 1-line
  follow-up edit to each is appropriate but is **not** part of this
  plan (the docs/ rule says no bundling of context-doc edits with
  src/test commits).

## Open questions

- **Pin vs. floor on `boltdb`.** Plan says `boltdb>=0.0.2` (floor).
  If the user wants a tighter pin (`boltdb==0.0.2`), it's a
  one-line change in the plan. Flagged for the implementer to
  confirm before landing.
- **Should `BoltDBKnownStateHandler` support a custom `BoltDB`
  client injection (like `AWSS3KnownStateHandler(bucket_name,
  *, client=...)` at `src/pylibreconcile/known_state/aws.py:14`)?**
  Useful for tests that want to mock. We've chosen **no** for V1 —
  the tests use a real file via `tmp_path`, and adding the kwarg
  means more API surface to maintain. If the user pushes back, it's
  a 5-line addition. Flagged.
- **Context manager protocol (`__enter__` / `__exit__`)?** Useful
  but not required. Left out of V1; can be added later without
  breaking anything. Flagged.
- **Multi-bucket per file?** Could expose
  `BoltDBKnownStateHandler(path, bucket_name="foo")` so multiple
  handlers share a file. Already supported via the existing
  `bucket_name` kwarg in our design (Locked decision 2). V1 keeps
  one bucket per handler instance — sharing is the caller's job.
  Flagged.

## What this plan does NOT include

- No changes to `Reconciler` or any consumer of
  `KnownStateHandler` — the new backend satisfies the protocol
  structurally.
- No changes to `docs/sphinx/` — autosummary picks it up.
- No changes to `docs/context/` — separate doc revision.
- No CI matrix expansion.
- No vendoring of boltdb.
- No changes to the existing JSON / YAML / Azure / AWS handlers.
- No new dependencies beyond `boltdb` itself.

## Next step (when implementation starts)

1. `uv add boltdb>=0.0.2` (per `AGENTS.md` Quick Recipes — use `uv
   add` for runtime deps, then `make install`, then `make all`).
2. Create `src/pylibreconcile/known_state/boltdb.py` per the class
   shape above.
3. Re-export from `src/pylibreconcile/known_state/__init__.py` and
   `src/pylibreconcile/__init__.py`.
4. Write `tests/known_state/boltdb_test.py` per the test list above.
   Add the protocol-membership assertion in
   `tests/known_state/protocol_test.py`.
5. Update `CHANGELOG.md`.
6. Land the four commits per "Commit plan."
7. Run `make all` and confirm everything is green. (pre-commit will
   have already run on each commit, but `make all` is the full gate.)

## Final step — rename this plan file (only after everything is done)

Once all four implementation commits are landed and `make all` is
green **and** the PR is open / merged, rename
`docs/plans/PLAN.md` to follow the project's zero-padded-numeric
filename convention (established by `0002-bootstrap-docs-context.md`
and locked in `docs/plans/0002-bootstrap-docs-context.md:84-87`).

Target filename:

```bash
git mv docs/plans/PLAN.md docs/plans/0003-add-boltdb-known-state-handler.md
```

**Important guards:**

- **ONLY rename after implementation is fully complete.** Do NOT
  rename mid-implementation. The file lives at `PLAN.md` while it
  is the live, in-flight plan so any agent or human reviewer can
  find it by the conventional name. Once work is done and the
  feature is shipped, this is the final housekeeping step.
- **Do NOT rename if work is abandoned.** If the plan is shelved or
  rejected, leave `PLAN.md` in place — it remains the authoritative
  record of what was considered.
- **Use `git mv`, not a delete + add.** Keeps history intact and
  shows up cleanly in `git log --follow`.
- **One extra commit for the rename**, separate from the four
  implementation commits, prefixed `chore(plans):`. Example:

  ```bash
  git add -A docs/plans/
  git commit -m "chore(plans): archive completed plan

  Rename docs/plans/PLAN.md to
  docs/plans/0003-add-boltdb-known-state-handler.md after the
  BoltDBKnownStateHandler work is complete and shipped."
  ```

- **This rename commit is the LAST commit on the branch.** No code,
  test, or doc edits belong in it. If you find yourself wanting to
  fix something while doing the rename, stop — that's a separate
  commit on a different branch / PR.
