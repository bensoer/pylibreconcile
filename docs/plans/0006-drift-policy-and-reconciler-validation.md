# Plan: `DriftPolicy` + `ImportPolicy` enums + `Reconciler` constructor validation

**Status:** drafting — ready for implementation. This plan lands the
policy layer that the
[`docs/investigations/wiring-container-investigation.md`](../investigations/wiring-container-investigation.md)
Questions 4 + 5 locked in, on top of the `WiringContainer` shipped by
[`0005-wiring-container.md`](0005-wiring-container.md).

The investigation is the *why*; this plan is the *what*. The
investigation should be read first for the design rationale behind
`DriftPolicy` values, the "validation lives on the `Reconciler`"
rule, and the `Change.action_performed` field.

**Scope of this plan:** add `DriftPolicy` and `ImportPolicy` enums;
add them as constructor parameters on `Reconciler`; add a
`_validate_wiring_for_settings()` method called from `Reconciler.__init__`;
add a `drift_policy` / `import_policy` per-call override on
`Reconciler.reconcile()`; add a new `Change.action_performed: bool`
field (defaults to `True`).

**Out of scope (planned separately):** the Seed 6 reconcile-loop
rewrite that *consumes* the policy knobs and actually populates
`Change.action_performed`. That plan will replace the current
`Reconciler.reconcile()` stub body with the full decision-matrix
loop.

---

## Goal

After this plan lands:

1. A caller can write

   ```python
   reconciler = Reconciler(
       desired_states=states,
       known_state_handler=LocalJSONKnownStateHandler(Path("state.json")),
       drift_policy=DriftPolicy.RECREATE,
       import_policy=ImportPolicy.WARN,
   )
   ```

   and the `Reconciler` validates at construction time that
   every `DesiredState` type in `states` has a `ResourceManager`
   wired in `WiringContainer` (because `RECREATE` requires it).

2. A caller who wants drift-only detection (no mutation) writes

   ```python
   reconciler = Reconciler(
       desired_states=states,
       known_state_handler=...,
       drift_policy=DriftPolicy.FLAG,
   )
   ```

   and the constructor accepts observer-only wiring (no
   `ResourceManager` required).

3. The `Change` dataclass has a new `action_performed: bool` field
   (default `True`) so the future reconcile loop can distinguish
   drift-was-flagged (`False`) from drift-was-recreated (`True`)
   without a refactor at that time.

4. `Reconciler.reconcile()` accepts per-call `drift_policy` and
   `import_policy` overrides (mirroring D-Q16's "constructor default
   + per-call override" pattern), even though the body is still a
   stub (Seed 6 consumes them).

This plan does **not** rewrite the `Reconciler.reconcile()` body.
The current stub (which just returns the input list unchanged)
stays. The future Seed 6 plan will replace it with the full
read-compare-emit loop that reads `KnownStateHandler`, consults
`WiringContainer().get(type(d))` per resource, applies the
effective policy, and emits `list[Change]` with `action_performed`
populated correctly.

---

## Locked decisions (carried from the investigation)

These are the constraints this plan must respect. Do not relax any
of them without an explicit user request that contradicts the
investigation.

| Decision | Resolution |
|---|---|
| `DriftPolicy` values | Three-value enum: `FLAG` / `RECREATE` / `ABSTAIN` (investigation lines 354-359) |
| `DriftPolicy` default | `FLAG` (investigation line 345) |
| `DriftPolicy.RECREATE` requires `ResourceManager` | Yes (investigation lines 361-364) |
| `DriftPolicy.FLAG` accepts observer-only | Yes (investigation line 363) |
| `DriftPolicy.ABSTAIN` accepts both kinds | Yes (investigation line 364) |
| Validation lives on `Reconciler`, not decorators | Confirmed (investigation lines 320-335) |
| Configuration-knob placement | Constructor default + per-call override (investigation lines 366-376, D-Q16) |
| `Change.action_performed: bool` (default `True`) | New field (investigation line 488) |
| `ImportPolicy` placement | Lands in same `policy.py` module (investigation lines 401-407 / 0005 deferral lines 1065-1067) |
| `ImportPolicy` values | Four-value enum: `AUTO` / `WARN` / `REJECT` / `SKIP` (D-Q9 lines 641-649) |
| `ImportPolicy` default | `WARN` (D-Q9 "warn" listed first as the recommended default) |
| `ObservedStateHandler` / `ResourceManager` separate | Confirmed (D-Q5) |
| `WiringContainer` singleton | Confirmed (0005) |
| `WiredResource` pair-wrapper | Not in V1 |
| Async / sync | Deferred. Sync V1. |

Investigation file:
[`docs/investigations/wiring-container-investigation.md:484-500`](../investigations/wiring-container-investigation.md).
Background decisions: [`0002-bootstrap-docs-context.md:582-649`](0002-bootstrap-docs-context.md)
(D-Q5, D-Q6, D-Q9, D-Q16, D-Q17).

---

## Background (what exists today)

### The shipped `WiringContainer`

[`0005-wiring-container.md`](0005-wiring-container.md) landed:

- `src/pylibreconcile/wiring/container.py` — `WiringContainer`
  singleton with `register(...)`, `get(...)`, MRO walk.
- `src/pylibreconcile/wiring/decorators.py` —
  `@register_observed_state_handler` and `@register_resource_manager`.
- `src/pylibreconcile/wiring/__init__.py` re-exports.
- Tests under `tests/wiring/` with an autouse fixture in
  `tests/wiring/conftest.py` that resets the singleton via
  `WiringContainer._instance = None` (per the merge resolution
  commit `0cd1247`).

The current `WiringContainer` API this plan consumes:

```python
class WiringContainer:
    def register(
        self,
        desired_state_type: type[DesiredState],
        observed_state_handler: ObservedStateHandler | None = None,
        resource_manager: ResourceManager | None = None,
    ) -> None: ...
    def get(
        self,
        desired_state_type: type[DesiredState],
    ) -> tuple[ObservedStateHandler | None, ResourceManager | None] | None: ...
```

Note: `get(...)` returns a `tuple`, which violates
`standards://python/syntax`'s "NEVER return tuples in methods. Return
DTOs" rule. This is a pre-existing deviation in shipped code and is
**not** corrected by this plan (touching it would require touching
every call site and every test, which is out of scope). New code in
this plan that consumes `WiringContainer().get(...)` simply
unpacks the tuple at the call site.

### Current `Reconciler` (stub)

[`src/pylibreconcile/reconciler.py`](../../src/pylibreconcile/reconciler.py) is
an 11-line stub:

```python
from collections.abc import Iterable

from .desired_state import DesiredState


class Reconciler:
    def __init__(self, desired_states: Iterable[DesiredState]) -> None:
        self._desired_states = list(desired_states)

    def reconcile(self) -> list[DesiredState]:
        return list(self._desired_states)
```

It takes **only** `desired_states` — no `known_state_handler`, no
policy knobs, no wiring lookups. This plan expands the constructor
to accept the full set of inputs the eventual reconcile loop will
need (per the design in [`0002-bootstrap-docs-context.md:582-649`](0002-bootstrap-docs-context.md)),
but keeps the body stubbed.

### Current `Change` (minimal)

[`src/pylibreconcile/change.py`](../../src/pylibreconcile/change.py):

```python
from dataclasses import dataclass
from enum import Enum

from .desired_state import DesiredState


class ChangeType(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class Change:
    type: ChangeType
    desired_state: DesiredState
```

This plan adds `action_performed: bool = True` as the third field.

### Current `tests/reconciler_test.py`

A single smoke test:

```python
def test_reconciler_iterable() -> None:
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler(states)
    result = reconciler.reconcile()
    assert len(result) == 2
```

This test must be updated because the `Reconciler.__init__`
signature is changing (now requires `known_state_handler`). The
update is mechanical — see "Test plan" below.

### Investigation's Questions 4 + 5 (already locked)

Read these sections of the investigation if designing the API:

- [`wiring-container-investigation.md:261-378`](../investigations/wiring-container-investigation.md)
  — drift-detection-without-correction rationale, validation
  layer placement, `DriftPolicy` enum shape, per-call override
  pattern.
- [`wiring-container-investigation.md:380-407`](../investigations/wiring-container-investigation.md)
  — adjacent surfaces advanced (Seed 3 partial close, Seed 6
  partial close via `action_performed`, Seed 7 advanced).
- [`0002-bootstrap-docs-context.md:641-649`](0002-bootstrap-docs-context.md)
  — D-Q9 (ImportPolicy modes) and D-Q16 (configuration layering).

---

## Scope boundary (in-scope vs. out-of-scope)

### In scope

1. New `src/pylibreconcile/policy.py` module with two enum classes:
   `DriftPolicy` (three values) and `ImportPolicy` (four values).
2. New constructor parameters on `Reconciler`:
   `known_state_handler: KnownStateHandler`,
   `drift_policy: DriftPolicy = DriftPolicy.FLAG`,
   `import_policy: ImportPolicy = ImportPolicy.WARN`.
3. New `_validate_wiring_for_settings()` private method on
   `Reconciler`, called from `Reconciler.__init__` after
   `self._desired_states` is stored.
4. New kwargs on `Reconciler.reconcile()`:
   `drift_policy: Optional[DriftPolicy] = None`,
   `import_policy: Optional[ImportPolicy] = None`. Stored on
   `self._effective_drift_policy` / `self._effective_import_policy`
   so the future Seed 6 plan can consume them. The reconcile body
   stays a stub (returns the input list).
5. New `Change.action_performed: bool = True` field. Default keeps
   existing callers compatible.
6. Updated `src/pylibreconcile/__init__.py` to re-export
   `DriftPolicy`, `ImportPolicy`.
7. New `policy.py` re-export from `src/pylibreconcile/__init__.py`.
8. Tests under `tests/reconciler/`: `policy_test.py`,
   `validation_test.py`, `reconciler_constructor_test.py`,
   `reconcile_override_test.py`, plus an `__init__.py` and
   `conftest.py` that resets `WiringContainer`.
9. Update `tests/reconciler_test.py` (the legacy smoke test) to
   pass the new required `known_state_handler` argument.
10. Doc updates: `docs/context/glossary.md` (add `DriftPolicy`,
    `ImportPolicy`), `docs/context/overview.md` (add a small
    note in the Reconciler section about policy knobs),
    `CHANGELOG.md` (`[Unreleased] / Added`).

### Out of scope

1. **The full reconcile-loop rewrite (Seed 6).** Future plan. The
   current `Reconciler.reconcile()` body stays a stub returning
   `list(self._desired_states)`. The future plan will rewrite it
   to read `KnownStateHandler`, consult
   `WiringContainer().get(type(d))`, classify via the decision
   matrix, apply the effective policy, and return
   `list[Change]` with `action_performed` populated.
2. **Renaming `ObservedStateManager` / `ResourceManager` to
   `*Interface`** (per `standards://python/syntax`). Project-wide
   refactor. Out of scope.
3. **Renaming `WiringContainer.get()` return shape** away from
   tuple to a DTO. Pre-existing deviation in shipped code.
4. **`WiredResource` pair-wrapper abstraction.** Explicitly deferred
   by the investigation.
5. **Async conversion of the protocols.** Sync V1.
6. **Per-`Reconciler` `WiringContainer` override.** Investigation
   lines 252-258 explicitly deferred this for V1.
7. **Per-resource policy overrides.** Not in V1.
8. **Drift-handling nuances beyond the three `DriftPolicy` values**
   (e.g. per-resource overrides, telemetry hooks). Investigation
   lines 504-514 deferred.
9. **Telemetry / logging.** Per `standards://python/logging`, loggers
   are class variables but are added when there's a real call site
   that needs them. The validation method does NOT need logging
   yet; if Seed 6 finds a logging use, it adds the loggers then.

---

## Design

### 1. `src/pylibreconcile/policy.py` (new module)

```python
from __future__ import annotations

from enum import Enum


class DriftPolicy(Enum):
    """How the Reconciler should respond to detected drift.

    Drift = Desired exists, Observed does not, Known exists.
    See `docs/context/overview.md` decision matrix.
    """

    FLAG = "FLAG"
    """Report drift via ``Change``; do not correct. Requires
    ``ObservedStateHandler`` only; ``ResourceManager`` optional."""

    RECREATE = "RECREATE"
    """Auto-correct drift by re-invoking the ``ResourceManager``'s
    ``create`` / ``update``. Requires a ``ResourceManager`` for every
    ``DesiredState`` type in scope."""

    ABSTAIN = "ABSTAIN"
    """Skip drift silently. ``ResourceManager`` may be present or
    absent; no validation against wiring."""


class ImportPolicy(Enum):
    """How the Reconciler should respond to detected import cases.

    Import = Desired exists, Observed exists, Known does not.
    See `docs/context/overview.md` decision matrix and D-Q9.
    """

    AUTO = "AUTO"
    """Auto-import and continue. Imported resource becomes managed."""

    WARN = "WARN"
    """Auto-import but include the imported item in the return value
    so the caller can log it. Default."""

    REJECT = "REJECT"
    """Raise / fail immediately on import detection."""

    SKIP = "SKIP"
    """Do nothing; leave the resource unmanaged; continue."""
```

**Naming rationale:**

- Per `standards://python/syntax`: "ALWAYS Postfix classes with
  appropriate pattern names that match the role of the class." The
  role here is "policy enum," so `Policy` postfix.
- `DriftPolicy` values are verb-form (`FLAG` / `RECREATE` /
  `ABSTAIN`) because they describe the *response* the reconciler
  takes when drift is detected.
- `ImportPolicy` values are also verb-form / state-form, matching
  D-Q9 verbatim (`auto` / `warn` / `reject` / `skip`). Uppercased
  to match the existing `ChangeType` enum's convention.

### 1b. `Configuration` dataclass (policy bundle)

Lives in `src/pylibreconcile/policy.py` alongside the two enums.
This dataclass bundles `DriftPolicy` and `ImportPolicy` into a single
parameter, so future expansion (retry settings, concurrency,
telemetry flags) adds fields to one object rather than individual
`Reconciler` parameters.

```python
@dataclass(frozen=True)
class Configuration:
    """Reconciler policy settings.

    All fields default to ``None``; call ``with_defaults()`` to
    resolve ``None`` fields to their system defaults. Pass per-call
    ``Configuration`` objects with only the fields you want to
    override set — ``applied_over`` merges non-``None`` fields
    over a base ``Configuration``.
    """

    drift_policy: DriftPolicy | None = None
    import_policy: ImportPolicy | None = None

    def with_defaults(self) -> Configuration:
        """Return a new ``Configuration`` with ``None`` fields replaced by
        their documented defaults (``DriftPolicy.FLAG``, ``ImportPolicy.WARN``).
        """
        return Configuration(
            drift_policy=self.drift_policy if self.drift_policy is not None else DriftPolicy.FLAG,
            import_policy=self.import_policy
            if self.import_policy is not None
            else ImportPolicy.WARN,
        )

    def applied_over(self, base: Configuration) -> Configuration:
        """Return a new ``Configuration`` where every **non-None** field in
        ``self`` replaces the corresponding field in ``base``.

        Used at ``reconcile()`` time: the per-call ``Configuration``
        overrides individual fields while inheriting the rest from
        the constructor's resolved ``Configuration``.
        """
        return Configuration(
            drift_policy=self.drift_policy if self.drift_policy is not None else base.drift_policy,
            import_policy=self.import_policy
            if self.import_policy is not None
            else base.import_policy,
        )
```

**Usage pattern:**

```python
# Constructor — all-None resolves to FLAG + WARN
r = Reconciler(states, handler)

# Constructor — explicit policies
r = Reconciler(
    states,
    handler,
    config=Configuration(
        drift_policy=DriftPolicy.RECREATE,
        import_policy=ImportPolicy.SKIP,
    ),
)

# Per-call override — only override drift, inherit import from constructor
r.reconcile(config=Configuration(drift_policy=DriftPolicy.ABSTAIN))
```

**Why `None`-with-defaults rather than concrete-defaults?** Per-call
overrides merge: when the caller sets only `drift_policy` on a
per-call `Configuration`, `import_policy` stays `None` so
`applied_over` falls back to the constructor's value. If the
dataclass had concrete defaults (`FLAG` / `WARN`), every per-call
override would implicitly reset every unset field to the system
default, even when the constructor had chosen something different.

### 2. `Reconciler` constructor + validation

`drift_policy` / `import_policy` become a single ``Configuration``
parameter (scales to future knobs like retry, concurrency, telemetry
without adding constructor params).

```python
# src/pylibreconcile/reconciler.py
from __future__ import annotations

from collections.abc import Iterable

from .desired_state import DesiredState
from .known_state import KnownStateHandler
from .policy import Configuration, DriftPolicy, ImportPolicy
from .wiring import WiringContainer


class Reconciler:
    def __init__(
        self,
        desired_states: Iterable[DesiredState],
        known_state_handler: KnownStateHandler,
        config: Configuration = Configuration(),
    ) -> None:
        self._desired_states = list(desired_states)
        self._known_state_handler = known_state_handler
        self._config = config.with_defaults()
        self._validate_wiring_for_settings()

    def _validate_wiring_for_settings(self) -> None:
        """Raise ``ValueError`` if the in-scope wiring doesn't satisfy the policy.

        Walks the unique ``DesiredState`` types in ``self._desired_states``,
        consults ``WiringContainer().get(type)`` for each (MRO-aware), and
        enforces:

        - ``DriftPolicy.RECREATE`` requires a ``ResourceManager`` for every
          type in scope.
        - Every type in scope must have *some* wiring (either observer or
          manager) — passing desired states with no wiring at all is
          always an error, regardless of policy.
        """
        unique_types: set[type[DesiredState]] = {type(d) for d in self._desired_states}
        missing: list[str] = []
        recreate_without_manager: list[str] = []
        for desired_state_type in unique_types:
            wiring = WiringContainer().get(desired_state_type)
            if wiring is None:
                missing.append(desired_state_type.__name__)
                continue
            observed, manager = wiring
            if observed is None and manager is None:
                missing.append(desired_state_type.__name__)
                continue
            if self._config.drift_policy is DriftPolicy.RECREATE and manager is None:
                recreate_without_manager.append(desired_state_type.__name__)
        if missing or recreate_without_manager:
            parts: list[str] = []
            if missing:
                parts.append(
                    "DesiredState types with no registered handlers: " + ", ".join(sorted(missing))
                )
            if recreate_without_manager:
                parts.append(
                    "DriftPolicy.RECREATE requires a ResourceManager for: "
                    + ", ".join(sorted(recreate_without_manager))
                )
            raise ValueError(
                "Reconciler.__init__: wiring does not satisfy policy. " + " | ".join(parts)
            )

    def reconcile(
        self,
        config: Configuration | None = None,
    ) -> list[DesiredState]:
        """One-pass reconcile. Body is a stub pending Seed 6.

        Per-call ``Configuration`` overrides the constructor's config:
        non-``None`` fields override, the rest are inherited from the
        constructor's resolved ``Configuration``.
        """
        if config is None:
            effective = self._config
        else:
            effective = config.applied_over(self._config)
        self._effective_config = effective
        self._validate_effective_policy_for_wiring(effective.drift_policy)
        return list(self._desired_states)

    def _validate_effective_policy_for_wiring(
        self,
        effective_drift: DriftPolicy,
    ) -> None:
        """Apply the same DriftPolicy.RECREATE check on a per-call override."""
        if effective_drift is not DriftPolicy.RECREATE:
            return
        unique_types: set[type[DesiredState]] = {type(d) for d in self._desired_states}
        recreate_without_manager: list[str] = []
        for desired_state_type in unique_types:
            wiring = WiringContainer().get(desired_state_type)
            if wiring is None:
                continue
            _observed, manager = wiring
            if manager is None:
                recreate_without_manager.append(desired_state_type.__name__)
        if recreate_without_manager:
            raise ValueError(
                "Reconciler.reconcile(drift_policy=RECREATE): "
                "missing ResourceManager for: " + ", ".join(sorted(recreate_without_manager))
            )
```

**Notes:**

- ``Configuration()`` (all-``None``) in the constructor resolves to
  ``FLAG`` + ``WARN`` via ``with_defaults()``.
- ``reconcile(config=Configuration(drift_policy=DriftPolicy.ABSTAIN))``
  overrides only ``drift_policy``; ``import_policy`` inherits from
  the constructor's config via ``applied_over``.
- Imports: ``Configuration`` from ``.policy``. No ``Mapping`` or
  ``Optional`` imports needed.
- ``DriftPolicy | None`` per the repo's ruff ``UP`` (pyupgrade) rule
  in ``pyproject.toml:118``.

### 3. `Change.action_performed` field

```python
# src/pylibreconcile/change.py (updated)
from dataclasses import dataclass
from enum import Enum

from .desired_state import DesiredState


class ChangeType(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class Change:
    type: ChangeType
    desired_state: DesiredState
    action_performed: bool = True
    """True if the Reconciler actually performed the action.

    False ONLY when drift was detected AND ``DriftPolicy.FLAG``
    caused the Reconciler to report the drift without recreating.
    All other code paths leave this True. The future reconcile
    loop (Seed 6) populates this correctly; today every Change
    that the existing code constructs will have the default True.
    """
```

**Notes:**

- Default `True` matches the investigation's locked decision
  (line 488).
- Position: third field. Existing callers using positional args
  will continue to work because they were passing two positional
  args; the new third field has a default and is keyword-only
  semantically.
- The `# Not sure if this is right` comment in the existing
  `change.py` (line 17) is removed — that ambiguity is resolved
  by this plan.

### 4. `__init__.py` re-exports

```python
# src/pylibreconcile/__init__.py (updated)
from .change import Change, ChangeType
from .desired_state import DesiredState
from .known_state import (
    AWSS3KnownStateHandler,
    AzureStorageKnownStateHandler,
    BoltDBKnownStateHandler,
    KnownStateHandler,
    LocalJSONKnownStateHandler,
    LocalYAMLKnownStateHandler,
    SQLiteKnownStateHandler,
)
from .policy import Configuration, DriftPolicy, ImportPolicy
from .reconciler import Reconciler
from .wiring import (
    WiringContainer,
    register_observed_state_handler,
    register_resource_manager,
)

__all__ = [
    "AWSS3KnownStateHandler",
    "AzureStorageKnownStateHandler",
    "BoltDBKnownStateHandler",
    "Change",
    "ChangeType",
    "Configuration",
    "DesiredState",
    "DriftPolicy",
    "ImportPolicy",
    "KnownStateHandler",
    "LocalJSONKnownStateHandler",
    "LocalYAMLKnownStateHandler",
    "Reconciler",
    "SQLiteKnownStateHandler",
    "WiringContainer",
    "register_observed_state_handler",
    "register_resource_manager",
]
```

---

## Files changed (exact list)

### New files

- `src/pylibreconcile/policy.py` — `DriftPolicy` and `ImportPolicy` enums.
- `tests/reconciler/__init__.py` — empty.
- `tests/reconciler/conftest.py` — autouse fixture resetting
  `WiringContainer._instance = None` (mirrors
  `tests/wiring/conftest.py`).
- `tests/reconciler/policy_test.py` — enum membership + value tests.
- `tests/reconciler/validation_test.py` — constructor validation
  against wiring.
- `tests/reconciler/reconciler_constructor_test.py` — constructor
  shape tests (defaults, kwargs, attributes stored).
- `tests/reconciler/reconcile_override_test.py` — per-call override
  kwargs validation.

### Edited files

- `src/pylibreconcile/policy.py` (new) — see Design §1.
- `src/pylibreconcile/reconciler.py` — full rewrite (11 lines →
  ~80 lines per Design §2). The new body adds the constructor
  parameters, the validation method, the per-call kwargs, and the
  effective-policy storage.
- `src/pylibreconcile/change.py` — add `action_performed: bool =
  True` field; remove the `# Not sure if this is right` comment.
- `src/pylibreconcile/__init__.py` — re-export `DriftPolicy`,
  `ImportPolicy`. Update `__all__`.
- `tests/reconciler_test.py` — update the legacy smoke test to
  pass a `known_state_handler` (see "Test plan" §"Legacy test
  update").
- `docs/context/glossary.md` — add `DriftPolicy`, `ImportPolicy`
  entries under "Plumbing / wiring".
- `docs/context/overview.md` — add a short note in the
  Reconciler section about policy knobs; do NOT rewrite the
  constructor sketch in lines 198-204 (that's Seed 6's concern).
- `CHANGELOG.md` — under `[Unreleased] / Added`, add bullets
  for `DriftPolicy`, `ImportPolicy`, `Reconciler` constructor
  validation, and `Change.action_performed`.

### Not changed (out of scope)

- `src/pylibreconcile/wiring/*` — no edits. `WiringContainer` is
  consumed as-is.
- `src/pylibreconcile/observed_state/*` and
  `src/pylibreconcile/resource_manager/*` — no edits.
- `src/pylibreconcile/desired_state/*` — no edits.
- `src/pylibreconcile/known_state/*` — no edits.
- `tests/wiring/*` — no edits. The autouse fixture in
  `tests/wiring/conftest.py` already resets the singleton; the
  new `tests/reconciler/conftest.py` mirrors it.
- `tests/core_test.py` — no edits.
- `tests/known_state/*` — no edits.
- `pyproject.toml`, `uv.lock`, `Makefile`, `AGENTS.md`,
  `.pre-commit-config.yaml`, `.opencode/rules/*` — no changes
  needed.
- CI / GitHub workflows — no changes.
- `docs/sphinx/*` — no changes. This plan only updates
  `docs/context/`.

### Pre-flight observations flagged (not fixed by this plan)

These are real issues spotted while drafting. They are flagged so
the implementer is not surprised; they are NOT part of this plan's
scope.

1. **`Reconciler.__init__` signature is a breaking change.** Adding
   the required `known_state_handler` parameter breaks the legacy
   `Reconciler(states)` constructor. There are no public callers
   using it (the library is pre-release at v0.1.0 per
   `pyproject.toml:3`), so this is acceptable. The legacy test
   `tests/reconciler_test.py:13` must be updated (see "Test plan"
   below).
2. **`WiringContainer.get()` returns a tuple.** Violates
   `standards://python/syntax`'s "NEVER return tuples" rule.
   Pre-existing deviation in shipped code. This plan consumes the
   tuple via unpacking — does NOT touch `WiringContainer`.
3. **The `DesiredState` base class is not decorated.** A caller
   passing a bare `DesiredState()` instance (no subclass) would
   trigger a "no registered handlers" error. This is intentional —
   the base class is abstract (it has no fields, no real use), but
   the validation should still error rather than silently no-op.
   Test covers this.
4. **`standards://python/syntax` says "ALWAYS postfix interface
   classes with `Interface`" and "NEVER use Protocol"**, but the
   existing protocols (`ObservedStateHandler`, `ResourceManager`,
   `KnownStateHandler`) are `@runtime_checkable` `Protocol`s. This
   is a pre-existing deviation, not corrected here.
5. **`KnownStateHandler` import path** is `from .known_state import
   KnownStateHandler` (the protocol class). The concrete handlers
   (`LocalJSONKnownStateHandler`, etc.) live in the same subpackage
   and are re-exported. The constructor signature uses the protocol
   class so callers can pass any backend.
6. **`tests/reconciler_test.py` (the legacy file at the repo
   root)** must be updated, NOT deleted. It contains a single
   smoke test. After update it can stay where it is (alongside
   the new `tests/reconciler/` package) or be moved into the new
   package. Plan keeps it at the repo root for minimal diff.

---

## Public API surface (what callers see)

After this plan lands, the public surface adds:

```python
# Enums
class DriftPolicy(Enum):
    FLAG = "FLAG"
    RECREATE = "RECREATE"
    ABSTAIN = "ABSTAIN"


class ImportPolicy(Enum):
    AUTO = "AUTO"
    WARN = "WARN"
    REJECT = "REJECT"
    SKIP = "SKIP"


# Configuration bundle
@dataclass(frozen=True)
class Configuration:
    drift_policy: DriftPolicy | None = None
    import_policy: ImportPolicy | None = None

    def with_defaults(self) -> Configuration: ...
    def applied_over(self, base: Configuration) -> Configuration: ...


# Reconciler
class Reconciler:
    def __init__(
        self,
        desired_states: Iterable[DesiredState],
        known_state_handler: KnownStateHandler,
        config: Configuration = Configuration(),
    ) -> None:
        # resolves None fields via with_defaults(), validates wiring
        ...

    def reconcile(
        self,
        config: Configuration | None = None,
    ) -> list[DesiredState]:
        # stub body; non-None config merges via applied_over()
        ...


# Change (new field)
@dataclass
class Change:
    type: ChangeType
    desired_state: DesiredState
    action_performed: bool = True
```

`Reconciler.reconcile()` still returns `list[DesiredState]` (the
stub body returns the input list unchanged). Seed 6 changes the
return type to `list[Change]` and writes the real loop.

---

## Test plan

All new tests live under `tests/reconciler/` (new package). The
legacy `tests/reconciler_test.py` (at the repo root) is updated,
not moved.

### `tests/reconciler/conftest.py`

Mirrors `tests/wiring/conftest.py`:

```python
import pytest

from pylibreconcile.wiring.container import WiringContainer


@pytest.fixture(autouse=True)
def _wiring_container_reset() -> None:
    WiringContainer._instance = None
```

### `tests/reconciler/policy_test.py`

- `test_drift_policy_has_three_values` — `len(DriftPolicy) == 3`.
- `test_drift_policy_values` — exact set `{FLAG, RECREATE,
  ABSTAIN}`.
- `test_import_policy_has_four_values` — `len(ImportPolicy) == 4`.
- `test_import_policy_values` — exact set `{AUTO, WARN, REJECT,
  SKIP}`.
- `test_drift_policy_values_are_uppercase_strings` — each enum
  value's `.value` is the same as `.name`. Defends against future
  renaming.
- `test_import_policy_values_are_uppercase_strings` — same.

### `tests/reconciler/validation_test.py`

All tests use `FakeObserver` / `FakeManager` helpers mirroring
`tests/wiring/container_test.py`.

- `test_constructor_accepts_observer_only_with_flag` — register
  observer-only, construct `Reconciler(drift_policy=FLAG)`,
  succeeds.
- `test_constructor_accepts_manager_only_with_flag` — register
  manager-only, construct with `FLAG`, succeeds.
- `test_constructor_accepts_both_with_flag` — register both,
  succeeds.
- `test_constructor_accepts_any_wiring_with_abstain` — register
  observer-only, manager-only, both; all three succeed with
  `ABSTAIN`.
- `test_constructor_recreate_requires_manager` — register
  observer-only, construct `Reconciler(drift_policy=RECREATE)`,
  raises `ValueError`. Error message mentions the offending
  type's name and the word "ResourceManager".
- `test_constructor_recreate_with_manager_succeeds` — register
  both, construct with `RECREATE`, succeeds.
- `test_constructor_rejects_no_wiring` — no decorator on the
  type, construct `Reconciler()`, raises `ValueError`. Error
  message mentions the type's name.
- `test_constructor_rejects_wiring_with_both_none` — manually
  call `WiringContainer().register(Type, None, None)` and expect
  it to raise (this protects the existing `register()` contract
  — does NOT change the validation rule).
- `test_constructor_validates_each_unique_type` — pass multiple
  instances of two different types; only one has wiring; verify
  the error mentions the unwired type and not the wired one.
- `test_constructor_uses_mro_walk` — register on parent type,
  pass instances of child type; succeeds (MRO walk returns
  parent's wiring).
- `test_constructor_mro_walk_with_recreate` — same as above but
  with `RECREATE`; parent has manager, succeeds.
- `test_constructor_mro_walk_recreate_without_manager` —
  register observer on parent, pass child instances with
  `RECREATE`; raises (child inherits observer-only via MRO,
  doesn't satisfy `RECREATE`).

### `tests/reconciler/reconciler_constructor_test.py`

- `test_constructor_stores_desired_states` — pass a list, verify
  `len(Reconciler._desired_states) == len(list)`.
- `test_constructor_stores_known_state_handler` — pass a handler,
  verify `Reconciler._known_state_handler is handler`.
- `test_constructor_default_drift_policy_is_flag` — no
  `drift_policy` kwarg, verify `Reconciler._drift_policy ==
  DriftPolicy.FLAG`.
- `test_constructor_default_import_policy_is_warn` — no
  `import_policy` kwarg, verify `Reconciler._import_policy ==
  ImportPolicy.WARN`.
- `test_constructor_keeps_explicit_policy` — pass
  `drift_policy=ABSTAIN`, verify stored value.
- `test_constructor_iterable_input_accepted` — pass a generator
  (e.g. `(d for d in states)`), succeeds.
- `test_constructor_empty_iterable_accepted` — pass `[]`, no
  validation error (no types in scope → nothing to validate).

### `tests/reconciler/reconcile_override_test.py`

- `test_reconcile_accepts_no_kwargs` — call `reconcile()` with
  no args; no error.
- `test_reconcile_accepts_drift_policy_override` — call with
  `drift_policy=FLAG`; no error.
- `test_reconcile_accepts_import_policy_override` — call with
  `import_policy=AUTO`; no error.
- `test_reconcile_stores_effective_drift_policy` — call with
  override; verify `Reconciler._effective_drift_policy ==
  override_value`.
- `test_reconcile_stores_effective_import_policy` — same.
- `test_reconcile_override_none_falls_back_to_constructor` —
  call with explicit `drift_policy=None`; verify effective is
  the constructor's stored value.
- `test_reconcile_recreate_override_validates_wiring` —
  constructor uses `FLAG`, call `reconcile(drift_policy=
  RECREATE)`, no manager wired → raises `ValueError`. (Catches
  the "caller upgrades policy per-call" mistake.)
- `test_reconcile_recreate_override_with_manager_succeeds` —
  register manager, override to `RECREATE`, succeeds.
- `test_reconcile_stub_returns_input_list` — pass three states,
  call `reconcile()`, assert `result == states` (identity on
  the list, since the stub returns `list(self._desired_states)`
  — a new list, so identity won't hold; assert by length and
  element identity: `result[0] is states[0]`, etc.).

### Legacy test update — `tests/reconciler_test.py`

Current:

```python
"""Tests for the reconciler module."""

from pylibreconcile import DesiredState, Reconciler


def test_reconciler_iterable() -> None:
    """Verify Reconciler works with an iterable of DesiredState."""

    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler(states)
    result = reconciler.reconcile()
    assert len(result) == 2
```

Updated:

```python
"""Tests for the reconciler module."""

from pathlib import Path

from pylibreconcile import (
    DesiredState,
    LocalJSONKnownStateHandler,
    Reconciler,
    register_observed_state_handler,
    register_resource_manager,
)


class FakeObserver:
    def exists(self, desired_state: DesiredState) -> bool:
        return True

    def is_match(self, desired_state: DesiredState) -> bool:
        return True


class FakeManager:
    def create(self, desired_state: DesiredState) -> None:
        pass

    def update(self, desired_state: DesiredState) -> None:
        pass

    def delete(self, desired_state: DesiredState) -> None:
        pass


@register_observed_state_handler(FakeObserver())
@register_resource_manager(FakeManager())
class ExampleState(DesiredState):
    id: int


def test_reconciler_iterable(tmp_path: Path) -> None:
    """Verify Reconciler works with an iterable of DesiredState."""
    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler(
        desired_states=states,
        known_state_handler=LocalJSONKnownStateHandler(tmp_path / "state.json"),
    )
    result = reconciler.reconcile()
    assert len(result) == 2
```

### Coverage target

`pyproject.toml` enforces coverage on `src/` (branch + line,
`pyproject.toml:85-103`). Aim for 100% on the new code
(`policy.py`) and the new branches in `reconciler.py` /
`change.py`. The validation method has a small number of branches
(per-policy + per-wiring combo) that are all testable.

---

## Implementation sequence

The implementer should follow this order to keep each commit
landable and `make all` green at every step. **This is the order
the commits land**, not necessarily the order the files are
written — files can be written ahead of time, but `git add` /
`git commit` happens in this order.

### Commit 1 — `feat(policy): add DriftPolicy, ImportPolicy, Reconciler validation, and Change.action_performed`

- **Files:**
  - **New** `src/pylibreconcile/policy.py` with `DriftPolicy` and
    `ImportPolicy`.
  - **Rewrite** `src/pylibreconcile/reconciler.py` with the new
    constructor, `_validate_wiring_for_settings`,
    `_validate_effective_policy_for_wiring`, and per-call override
    kwargs on `reconcile()`.
  - **Edit** `src/pylibreconcile/change.py` — add
    `action_performed: bool = True`; remove the `# Not sure if
    this is right` comment.
  - **Edit** `src/pylibreconcile/__init__.py` — re-export
    `DriftPolicy`, `ImportPolicy`; update `__all__`.
- **NOT edited:** `src/pylibreconcile/wiring/*` — no edits.
- **Verification before commit:**
  `python -c "from pylibreconcile import DriftPolicy, ImportPolicy, Reconciler, Change; print(DriftPolicy.FLAG, ImportPolicy.WARN, Change.__dataclass_fields__['action_performed'])"`
  succeeds.
- **Run:** `make lint format-check typecheck`. (Tests not
  required yet — the test commit is next. The pre-existing
  legacy `tests/reconciler_test.py` will break at this point
  because it doesn't pass `known_state_handler` — that's
  expected and is fixed in the test commit.)
- **Commit message:**
  `feat(policy): add DriftPolicy/ImportPolicy enums and Reconciler validation`

### Commit 2 — `test(policy): cover policy enums, validation, constructor, and reconcile override`

- **Files:** all the new test files listed in "Test plan":
  - `tests/reconciler/__init__.py`
  - `tests/reconciler/conftest.py`
  - `tests/reconciler/policy_test.py`
  - `tests/reconciler/validation_test.py`
  - `tests/reconciler/reconciler_constructor_test.py`
  - `tests/reconciler/reconcile_override_test.py`
  - **Update** `tests/reconciler_test.py` (the legacy smoke
    test) to pass `known_state_handler` and add decorators on
    `ExampleState`.
- **Verification:** `make test tests/reconciler/
  tests/reconciler_test.py` passes with full coverage on the
  new code. Existing `tests/wiring/*` still passes (the
  autouse fixture in their conftest is unchanged).
- **Commit message:**
  `test(policy): cover enums, validation, constructor, and reconcile override`

### Commit 3 — `docs(policy): document policy enums and Reconciler validation`

- **Files:**
  - `docs/context/glossary.md` — add `DriftPolicy`,
    `ImportPolicy` entries under "Plumbing / wiring". Update
    the existing `ImportPolicy` entry (it lists modes
    `auto`/`warn`/`reject`/`skip` lowercase — update to
    `AUTO`/`WARN`/`REJECT`/`SKIP` uppercase to match the
    enum, and add a "Placement" note mirroring the existing
    one).
  - `docs/context/overview.md` — add a short note in the
    Reconciler section about policy knobs (one or two
    sentences). Do NOT rewrite the constructor sketch in
    lines 198-204 — that's Seed 6.
  - `CHANGELOG.md` — under `[Unreleased] / Added`, add
    bullets for `DriftPolicy`, `ImportPolicy`, `Reconciler`
    constructor validation, and `Change.action_performed`.
- **Commit message:**
  `docs(policy): document enums, validation, and Change.action_performed`

### Final verification

After all three commits:

```bash
make all    # lint + format-check + typecheck + security + test
```

Must be green. All existing tests must continue to pass (the
`tests/wiring/*` suite is unaffected; the legacy
`tests/reconciler_test.py` is updated to the new signature; the
`tests/known_state/*` and `tests/core_test.py` suites are
unaffected).

---

## Commit plan (formal, per `.opencode/rules/separate-commits.md`)

The project rule is: stage `src/`, `tests/`, and `docs/` as
separate commits; tooling changes are their own commit;
Conventional Commits prefixes required. This plan has **no
tooling changes** — all three commits fall into the three
categories.

| # | Prefix | Scope | Files |
|---|---|---|---|
| 1 | `feat(policy)` | src | `src/pylibreconcile/policy.py` (new), `src/pylibreconcile/reconciler.py` (rewrite), `src/pylibreconcile/change.py` (edit), `src/pylibreconcile/__init__.py` (edit) |
| 2 | `test(policy)` | tests | `tests/reconciler/__init__.py` (new), `tests/reconciler/conftest.py` (new), `tests/reconciler/policy_test.py` (new), `tests/reconciler/validation_test.py` (new), `tests/reconciler/reconciler_constructor_test.py` (new), `tests/reconciler/reconcile_override_test.py` (new), `tests/reconciler_test.py` (edit) |
| 3 | `docs(policy)` | docs | `docs/context/glossary.md`, `docs/context/overview.md`, `CHANGELOG.md` |

Three commits, clean scope, Conventional Commits prefixes.

---

## Open questions (for future plans, not blockers for this one)

These are deliberately deferred to follow-up plans:

1. **The Seed 6 reconcile-loop rewrite.** The plan that *uses*
   the policy knobs and actually populates `Change.action_performed`.
   This plan lands the policy plumbing; Seed 6 lands the loop.
2. **Async / sync on protocols.** Sync V1.
3. **`WiredResource` pair-wrapper.** Explicitly deferred by the
   investigation (line 438-442).
4. **Per-`Reconciler` `WiringContainer` override.** Investigation
   lines 252-258 explicitly deferred for V1.
5. **Per-resource policy overrides.** Not in V1.
6. **Drift-handling nuances beyond the three `DriftPolicy`
   values.** Investigation lines 504-514.
7. **`WiringContainer.get()` returning a tuple** instead of a
   DTO. Pre-existing deviation in shipped code; would be a
   refactor that touches every consumer.

---

## Risks and edge cases

- **Validation walking `WiringContainer` per construction.**
  Cheap: `get(...)` is O(MRO depth) which is typically 3-5. The
  unique-types set comprehension is O(n) in desired-state count.
  No performance concern at typical caller scale.
- **`DesiredState` base class passed as an instance.** The
  validation should still error because the base class has no
  wiring. This is intentional — see pre-flight observation 3.
- **`from __future__ import annotations` interaction with
  `Enum`.** `Enum` subclasses work fine with future-imported
  annotations; no special handling needed.
- **`Iterable[DesiredState]` materialised to `list` in `__init__`.**
  Matches the existing behaviour. The future Seed 6 plan will
  preserve this (it's idempotent and the per-pass state).
- **Per-call override validation vs. constructor validation.**
  These are intentionally separate methods to keep the error
  messages distinct. A caller seeing
  `Reconciler.__init__: ...` knows they configured wrong at
  construction; a caller seeing
  `Reconciler.reconcile(drift_policy=RECREATE): ...` knows they
  upgraded wrong at call time.
- **Singleton + tests.** The `WiringContainer` is process-wide.
  `tests/reconciler/conftest.py` resets it before every test
  (mirroring `tests/wiring/conftest.py`). Without this,
  decorators from earlier tests would leak.
- **Default policy choice.** `DriftPolicy.FLAG` as the default
  matches the investigation's locked decision (line 345). This
  is the safest default — observation-only users get drift
  reports without forced mutation; full reconcilers explicitly
  opt into `RECREATE`.

---

## What this plan does NOT include

- No reconcile-loop rewrite (Seed 6 — separate plan).
- No async conversion of the protocols (sync V1).
- No `WiredResource` pair-wrapper abstraction.
- No per-`Reconciler` `WiringContainer` override.
- No per-resource policy overrides.
- No telemetry / logging (loggers are added when there's a real
  call site, per `standards://python/logging`).
- No `ObservedStateHandler` / `ResourceManager` rename to
  `*Interface` (project-wide refactor).
- No `WiringContainer.get()` return-shape refactor (pre-existing
  tuple deviation; out of scope).
- No runtime dependency changes (`pyproject.toml` / `uv.lock`
  untouched).
- No CI / GitHub workflow changes.
- No Sphinx doc changes (`docs/sphinx/` is the hosted user docs;
  this plan only updates `docs/context/`).
- No `tests/wiring/*` changes.
- No `tests/core_test.py` / `tests/known_state/*` changes.

---

## Final step — rename this plan file (only after everything is done)

Once all three implementation commits are landed and `make all`
is green **and** the PR is open, rename `docs/plans/PLAN.md` to
follow the project's zero-padded-numeric filename convention
(established by `0002-bootstrap-docs-context.md`,
`0003-add-boltdb-known-state-handler.md`,
`0004-sqlite-known-state-handler.md`, and
`0005-wiring-container.md`).

Target filename:

```bash
git mv docs/plans/PLAN.md docs/plans/0006-drift-policy-and-reconciler-validation.md
```

**Important guards (mirrored from
[`0005-wiring-container.md:1204-1241`](0005-wiring-container.md)
and [`0003-add-boltdb-known-state-handler.md:506-540`](0003-add-boltdb-known-state-handler.md)):**

- **ONLY rename after implementation is fully complete.** Do NOT
  rename mid-implementation. The file lives at `PLAN.md` while
  it is the live, in-flight plan so any agent or human reviewer
  can find it by the conventional name. Once work is done and
  the feature is shipped, this is the final housekeeping step.
- **Do NOT rename if work is abandoned.** If the plan is
  shelved or rejected, leave `PLAN.md` in place — it remains
  the authoritative record of what was considered.
- **Use `git mv`, not a delete + add.** Keeps history intact and
  shows up cleanly in `git log --follow`.
- **One extra commit for the rename**, separate from the three
  implementation commits, prefixed `chore(plans):`. Example:

  ```bash
  git add -A docs/plans/
  git commit -m "chore(plans): archive completed plan

  Rename docs/plans/PLAN.md to
  docs/plans/0006-drift-policy-and-reconciler-validation.md
  after the DriftPolicy + Reconciler validation work is
  complete and shipped."
  ```

- **This rename commit is the LAST commit on the branch.** No
  code, test, or doc edits belong in it. If you find yourself
  wanting to fix something while doing the rename, stop —
  that's a separate commit on a different branch / PR.
- **Per AGENTS.md rule 12: agents open PRs but do NOT merge
  them.** The merge is exclusively a human action.
