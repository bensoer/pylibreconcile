# Plan: Wiring container + per-`DesiredState` decorator-based registration

**Status:** drafting — ready for implementation. This plan lands the
core wiring layer from
[`docs/investigations/wiring-container-investigation.md`](../investigations/wiring-container-investigation.md):
the `WiringContainer` singleton and the two registration decorators.
It is the *what*; the investigation is the *why*.

**Scope of this plan:** Questions 1, 2, and 3 from the investigation
(lookup mechanism, registry location, singleton enforcement).

**Out of scope for this plan (planned separately):** Question 4
(`DriftPolicy` enum + `Reconciler` validation + `Change.action_performed`)
and Question 5 (validation of registration-vs-policy). These are
closely related — they're the natural next layer after decorators
exist — but they are deliberately not bundled here. A future
`0005-drift-policy-and-reconciler-validation.md` plan will cover
them.

**Also out of scope:** the broken `Reconciler.get_change_set` body
that references non-existent `KnownStateHandler` methods. That is a
separate refactor (the future Seed 6 reconcile-loop re-architecture
that will *use* the `WiringContainer` this plan lands).

---

## Goal

After this plan lands, a caller can write

```python
@pylibreconcile.register_observed_state_handler(
    ServerObservedStateHandler(api_client),
)
@pylibreconcile.register_resource_manager(
    ServerResourceManager(api_client),
)
class ServerDesired(DesiredState):
    hostname: str
    port: int
```

and the handlers are discoverable — they live in the
`WiringContainer` singleton, ready for a future `Reconciler` to
look them up per-`DesiredState` type. The decorators themselves
are the entire V1 surface this plan delivers.

This plan does **not** touch the `Reconciler`, does **not** add
`DriftPolicy`, does **not** modify `Change`, and does **not**
modify `DesiredState.__init_subclass__`. The wiring layer is
standalone; downstream consumers can be wired up in follow-up
plans.

---

## Locked decisions (carried from the investigation)

These are the constraints this plan must respect. Do not relax
any of them without an explicit user request that contradicts
the investigation.

| Decision | Resolution |
|---|---|
| Lookup mechanism (Seed 1) | Two decorators: `@register_observed_state_handler(instance)` and `@register_resource_manager(instance)` |
| Registry location | External `WiringContainer` class; **not** on `DesiredState` as class attrs |
| Singleton enforcement | `__new__`-based, exactly one instance per process |
| Class name suffix | `Container` (matches DI-container vocabulary; satisfies `standards://python/syntax` "Postfix classes with appropriate pattern names") |
| Mutual-presence at decoration time | **Not required.** Each decorator is independent. Either or both may be applied. |
| `ObservedStateHandler` and `ResourceManager` protocols | **Stay separate** (D-Q5 reaffirmed) |
| `WiredResource` combined class | **Not in V1.** Deferred. |
| Async / sync | Deferred. Sync V1. |
| `WiringContainer` scope | Narrow: `DesiredState`-to-handlers only. No logging/telemetry resolution. |

Investigation file:
[`docs/investigations/wiring-container-investigation.md:484-500`](../investigations/wiring-container-investigation.md).

**Note:** the investigation also locks `DriftPolicy` (Question 4),
`Change.action_performed` (Question 5), and the rule that "validation
lives on the `Reconciler`, not on the decorators." All three remain
locked decisions for the *project*, but they are **not** the scope
of this plan. The decorators are intentionally policy-blind: they
just register. The future `DriftPolicy` plan will add the
`Reconciler` validation layer on top.

---

## Background (what exists today)

The investigation builds on three resolved design decisions in
[`docs/plans/0002-bootstrap-docs-context.md`](../plans/0002-bootstrap-docs-context.md):

- **D-Q5** (Observed vs. ResourceManager component shape, lines 582-596): the read-side and write-side are separate protocols.
- **D-Q6** (Per-type vs. global wiring, lines 598-604): wiring is per-`DesiredState` type.
- **D-Q16** (`ImportPolicy` placement, lines 688-694): configuration knobs land on the `Reconciler` as constructor defaults with per-call overrides. The future `DriftPolicy` plan will follow this pattern (out of scope here).

The conceptual split is also documented in
[`docs/context/overview.md:75-88`](../context/overview.md) and
[`docs/context/glossary.md:81-90`](../context/glossary.md).

### Current state of the source tree

The repo is mid-refactor. The following has been observed while
investigating this plan and is *not* part of this plan's scope to
*fix*, but the implementer MUST be aware:

- **`src/pylibreconcile/core.py` is empty (1 byte)** — `git diff HEAD
  src/pylibreconcile/core.py` shows the entire 15-line `DesiredState`
  class was deleted.
- **`src/pylibreconcile/desired_state/models.py`** holds the actual
  `DesiredState` class (with `__init_subclass__` that auto-applies
  `@dataclass` and a `to_hash()` method). The investigation's
  sketch says this is the place to add the registration hook — but
  as documented in Design §2, that sketch is technically incorrect
  (decorators run after `__init_subclass__`), so this file is NOT
  edited in this plan.
- **`src/pylibreconcile/__init__.py`** still imports `DesiredState`
  from `.core`, not from `.desired_state`. **This is a pre-existing
  import bug that breaks the whole test suite today.** The
  implementer must fix it as part of the `src/` commit in this plan
  (see "Pre-flight observations" at the end — this is the only
  place a fix like that belongs because the bug is on the critical
  path of the wiring layer being importable).
- **`src/pylibreconcile/observed_state/protocol.py`** defines
  `ObservedStateHandler` as a `@runtime_checkable` `Protocol` with
  `exists(desired_state)` and `is_match(desired_state)`.
- **`src/pylibreconcile/resource_manager/protocol.py`** defines
  `ResourceManager` as a `@runtime_checkable` `Protocol` with
  `create(desired_state)`, `update(desired_state)`, and
  `delete(desired_state)`.
- **`src/pylibreconcile/change.py`** (untracked) defines `ChangeType`
  enum (`CREATE`/`UPDATE`/`DELETE`) and a `Change` dataclass with
  `type: ChangeType` and `desired_state: DesiredState` fields. This
  plan commits it as-is — no `action_performed` field, no other
  changes.
- **`src/pylibreconcile/reconciler.py`** is currently in a broken
  in-between state — it takes a `known_state_handler`, but calls
  methods (`exists`, `is_match`, `get_all`) that don't exist on the
  `KnownStateHandler` protocol (`has_key`, `get_all_keys`,
  `get_value`, `set_value`). **This plan does not touch
  `Reconciler`** — no edits, no new methods, no new constructor
  parameters. The broken body stays broken; fixing it is a
  separate refactor (Seed 6 — the reconcile-loop re-architecture
  that will *use* the `WiringContainer` this plan lands).

### Existing tests

- `tests/core_test.py` (363 lines) — covers `DesiredState`
  dataclass transformation, hashing, inheritance (multi-level,
  5-level), `ClassVar` exclusion, and cooperative
  `__init_subclass__`. **All of these need to keep passing.**
- `tests/reconciler_test.py` — minimal smoke test
  (`Reconciler(states)` constructor; one `reconcile()` call). **Will
  need to be updated because the current `Reconciler.__init__`
  signature is changing.** See "Test plan" below.
- `tests/known_state/*.py` — KnownState handler tests, unaffected by
  this plan.

---

## Scope boundary (in-scope vs. out-of-scope)

This plan delivers exactly **two things**, plus the minimum
infrastructure needed to make them importable:

1. **`WiringContainer`** — singleton DI container at
   `src/pylibreconcile/wiring/container.py`. Registers handler
   instances keyed by `DesiredState` *type* (with MRO walk on
   `get`). Re-exported as `pylibreconcile.WiringContainer`.
2. **Two decorators** —
   `pylibreconcile.register_observed_state_handler` and
   `pylibreconcile.register_resource_manager`. Each registers its
   instance directly with `WiringContainer` at decoration time, via
   a private `_register_pair` helper that merges partial
   registrations (so applying both decorators to the same class
   produces a single combined entry).

**No edits to `__init_subclass__` on `DesiredState`** — the
existing `__init_subclass__` keeps its single job
(auto-applying `@dataclass`) and is otherwise untouched. See the
technical correction in section 2 of "Design" for why this differs
from the investigation's sketch.

This plan does **not** include:

- **`DriftPolicy`** (Question 4 in the investigation). The
  `FLAG` / `RECREATE` / `ABSTAIN` enum, the `Reconciler.__init__`
  parameter, the per-call `reconcile()` override, and
  `_validate_wiring_for_settings` are all out of scope. They
  belong to a future `0005-drift-policy-and-reconciler-validation.md`
  plan that will build on top of this one.
- **`Change.action_performed`** (Question 5 in the investigation).
  The `bool` field that distinguishes drift-was-flagged from
  drift-was-recreated is out of scope; it depends on the future
  reconcile loop (Seed 6) actually populating it. Out of scope.
- **`Reconciler` class — entirely untouched.** No constructor
  changes, no new methods, no per-call overrides. The plan only
  fixes the broken import path in `src/pylibreconcile/__init__.py`
  (see Pre-flight observation 1).
- The full `Reconciler.reconcile()` re-architecture that consults
  the `WiringContainer` per-resource. That's a future plan seed
  (Seed 6 in
  [`0002-bootstrap-docs-context.md:949-963`](../plans/0002-bootstrap-docs-context.md)).
- `ImportPolicy` (Seed 7 in the same file).
- `WiredResource` pair-wrapper abstraction (explicitly deferred by
  the investigation, line 438-442).
- Async conversion of the protocols (Seed 1 sub-question).
- The pre-existing `Reconciler` ↔ `KnownStateHandler` method-name
  drift in `src/pylibreconcile/reconciler.py` (the broken methods
  `exists` / `is_match` / `get_all` are out of scope). See
  "Pre-flight observations".

---

## Design

### 1. `WiringContainer` — `src/pylibreconcile/wiring/container.py`

New file. New subpackage `src/pylibreconcile/wiring/` with
`__init__.py` re-exporting `WiringContainer`.

```python
# src/pylibreconcile/wiring/container.py
from __future__ import annotations

from typing import Optional

from ..desired_state import DesiredState
from ..observed_state import ObservedStateHandler
from ..resource_manager import ResourceManager


class WiringContainer:
    """Singleton DI container for DesiredState wiring.

    Exactly one instance per process. Constructing the class returns
    the same object every time. Tests clear it via :meth:`clear`.

    Scope is narrow: maps ``type[DesiredState]`` to its (optional)
    ``ObservedStateHandler`` and (optional) ``ResourceManager``. No
    logging, telemetry, or other resolution concerns.
    """

    _instance: Optional[WiringContainer] = None
    _wiring: dict[
        type[DesiredState], tuple[Optional[ObservedStateHandler], Optional[ResourceManager]]
    ]

    def __new__(cls) -> WiringContainer:
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._wiring = {}
            cls._instance = inst
        return cls._instance

    def register(
        self,
        desired_state_type: type[DesiredState],
        observed_state_handler: Optional[ObservedStateHandler] = None,
        resource_manager: Optional[ResourceManager] = None,
    ) -> None:
        if observed_state_handler is None and resource_manager is None:
            raise ValueError(
                f"register({desired_state_type.__name__}): at least one of "
                "observed_state_handler or resource_manager must be non-None"
            )
        self._wiring[desired_state_type] = (
            observed_state_handler,
            resource_manager,
        )

    def get(
        self,
        desired_state_type: type[DesiredState],
    ) -> Optional[tuple[Optional[ObservedStateHandler], Optional[ResourceManager]]]:
        """Walk the type's MRO; return first hit or ``None`` if no wiring exists."""
        for klass in desired_state_type.__mro__:
            if klass in self._wiring:
                return self._wiring[klass]
        return None

    def clear(self) -> None:
        """Reset the registry. Used by tests; not for production callers."""
        self._wiring.clear()
```

**Notes:**

- `_wiring` is keyed by the exact `type[DesiredState]` that the
  decorators were applied to (e.g. `class ServerDesired(DesiredState)`
  decorated → `dict[ServerDesired, ...]`). On `get`, we walk the
  MRO so an undecorated subclass inherits its parent's wiring —
  this is the behaviour the user explicitly wants (the
  investigation points at `tests/core_test.py:232-290` as the
  precedent for multi-level inheritance).
- `register` raises `ValueError` if both args are `None` — this is
  the *only* registration-time validation. The "does this match the
  policy?" validation lives on the `Reconciler`.
- `clear()` is intentionally public. Tests call
  `WiringContainer().clear()` between cases. Production callers
  should not.
- `_instance` and `_wiring` use `from __future__ import annotations`
  so the `_wiring` dict can refer to types not yet imported at module
  load time without a runtime cost.

### 2. Decorators — `src/pylibreconcile/wiring/decorators.py`

New file in the same subpackage.

> **Technical correction (deviation from the investigation's
> sketch):** the investigation's locked decisions are:
> (1) two decorators, (2) external `WiringContainer`,
> (3) mutual-presence not required. The investigation's *sketch*
> also describes "`__init_subclass__` reads both `ClassVar`
> markers" — this sketch is **technically impossible** with
> standard Python decorator semantics, because decorators run
> *after* `__init_subclass__`. I verified this experimentally
> (decorator execution order: `__init_subclass__` first, then
> decorators on the class body). The right correction is to
> have the **decorators register directly** with
> `WiringContainer`. This preserves all three locked decisions
> and removes the need for `ClassVar` plumbing on
> `DesiredState`. The "decoration is presentation, container is
> the source of truth, validation is on `Reconciler`" layering
> the investigation locked in (lines 320-335) is preserved.

```python
# src/pylibreconcile/wiring/decorators.py
from __future__ import annotations

from typing import Callable, TypeVar

from ..desired_state import DesiredState
from ..observed_state import ObservedStateHandler
from ..resource_manager import ResourceManager

_T = TypeVar("_T", bound=type[DesiredState])


def register_observed_state_handler(
    instance: ObservedStateHandler,
) -> Callable[[_T], _T]:
    """Class decorator: bind an ObservedStateHandler to a DesiredState subclass.

    Usage::

        @pylibreconcile.register_observed_state_handler(
            ServerObservedStateHandler(api_client),
        )
        class ServerDesired(DesiredState):
            hostname: str
            port: int

    The handler instance is registered with ``WiringContainer``
    immediately at decoration time. Independent of
    ``@register_resource_manager``: either or both may be applied.
    """

    def decorator(cls: _T) -> _T:
        # Read the current ResourceManager registration (if any) so
        # we don't clobber a manager that @register_resource_manager
        # already stored. _REGISTRATIONS is a private dict the
        # container exposes only to the decorators (see
        # WiringContainer._register_pair below).
        from .container import WiringContainer

        WiringContainer()._register_pair(
            desired_state_type=cls,
            observed_state_handler=instance,
        )
        return cls

    return decorator


def register_resource_manager(
    instance: ResourceManager,
) -> Callable[[_T], _T]:
    """Class decorator: bind a ResourceManager to a DesiredState subclass.

    Usage::

        @pylibreconcile.register_resource_manager(
            ServerResourceManager(api_client),
        )
        class ServerDesired(DesiredState):
            hostname: str
            port: int

    The manager instance is registered with ``WiringContainer``
    immediately at decoration time. Independent of
    ``@register_observed_state_handler``: either or both may be applied.
    """

    def decorator(cls: _T) -> _T:
        from .container import WiringContainer

        WiringContainer()._register_pair(
            desired_state_type=cls,
            resource_manager=instance,
        )
        return cls

    return decorator
```

**Notes:**

- The decorators **register directly** with `WiringContainer`
  using a private `_register_pair` method that handles "merge with
  existing partial registration" (so applying both decorators
  produces a single combined entry, not two overwrite-each-other
  entries).
- The decorators return `cls` unchanged. They're registration
  triggers, not transformers.
- `mypy strict` with `disallow_untyped_decorators = true` is
  enabled (see `pyproject.toml:157`). The type signature above
  uses `TypeVar` bounded by `type[DesiredState]` to satisfy this.

### `WiringContainer._register_pair` (the private API the decorators use)

```python
# Inside WiringContainer (src/pylibreconcile/wiring/container.py)


def _register_pair(
    self,
    desired_state_type: type[DesiredState],
    observed_state_handler: Optional[ObservedStateHandler] = None,
    resource_manager: Optional[ResourceManager] = None,
) -> None:
    """Private. Called by the @register_* decorators.

    Merges with any existing partial registration for this type:
    if @register_observed_state_handler ran first and stored only
    the observer, and then @register_resource_manager runs, the
    second call sees the existing observer and stores the union.
    """
    existing = self._wiring.get(desired_state_type)
    if existing is not None:
        prev_observed, prev_manager = existing
        observed_state_handler = (
            observed_state_handler if observed_state_handler is not None else prev_observed
        )
        resource_manager = resource_manager if resource_manager is not None else prev_manager
    self.register(
        desired_state_type=desired_state_type,
        observed_state_handler=observed_state_handler,
        resource_manager=resource_manager,
    )
```

**Note:** `_register_pair` delegates to the public `register`
method, which still enforces "at least one non-None" via
`ValueError`. So the first decorator on a class succeeds (it has
its handler non-None), and the second decorator on the same class
merges then re-checks (also succeeds because at least one is
non-None).

### 3. `__init_subclass__` — **unchanged**

**Critical clarification:** the plan does **not** add a
registration step to `__init_subclass__`. The existing
`__init_subclass__` at `src/pylibreconcile/desired_state/models.py:7-10`
keeps its single job — auto-applying `@dataclass` — and is
**otherwise untouched**. Registration happens in the decorators,
not in `__init_subclass__`.

This means `src/pylibreconcile/desired_state/models.py` requires
**no edits** beyond what's already there. The investigation's
"`__init_subclass__` reads both `ClassVar` markers" sketch is
replaced by the technically-correct "decorators register directly"
pattern.

### Out of scope (deferred to a follow-up plan)

The investigation's Question 4 (`DriftPolicy`) and Question 5
(validation of registration-vs-policy) are deliberately NOT in this
plan. They require:

- A new `DriftPolicy` enum at `src/pylibreconcile/policy.py`.
- A new `_validate_wiring_for_settings()` method on `Reconciler`,
  called from `__init__`, that walks the `WiringContainer` and
  asserts wiring-shape requirements (e.g. `RECREATE` requires a
  `ResourceManager`).
- A `DriftPolicy` constructor parameter on `Reconciler` and a
  per-call `reconcile()` override.
- A new `action_performed: bool` field on `Change` (default
  `True`), distinguishing drift-was-flagged (`False`) from
  drift-was-recreated (`True`).
- Touching the existing broken `Reconciler.reconcile()` /
  `get_change_set` bodies — which is *itself* a separate refactor
  (Seed 6) that needs the `WiringContainer` to be available first
  (this plan provides that).

These all build on top of the `WiringContainer` this plan lands,
and they all need a coherent design conversation before code
lands. A future `0005-drift-policy-and-reconciler-validation.md`
plan will translate Questions 4 + 5 of the investigation into a
concrete contract.

**What this plan leaves intact:**

- `src/pylibreconcile/reconciler.py` — completely untouched. No
  new imports, no new constructor parameters, no new methods, no
  per-call overrides.
- `src/pylibreconcile/change.py` — committed as-is (it's
  currently untracked). No new fields. The future `DriftPolicy`
  plan will add `action_performed` then.
- `src/pylibreconcile/desired_state/models.py` — completely
  untouched. `__init_subclass__` continues its single job of
  auto-applying `@dataclass`.

### 4. `__init__.py` updates

`src/pylibreconcile/__init__.py` currently imports `DesiredState`
from `.core` (broken). This plan fixes it as part of the `src/`
commit. The existing untracked `change.py` is added to the public
exports here too (it has nothing in-scope to add; it's just landed
alongside).

```python
# src/pylibreconcile/__init__.py (updated)
from .desired_state import DesiredState
from .change import Change, ChangeType
from .known_state import (
    AWSS3KnownStateHandler,
    AzureStorageKnownStateHandler,
    BoltDBKnownStateHandler,
    KnownStateHandler,
    LocalJSONKnownStateHandler,
    LocalYAMLKnownStateHandler,
)
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
    "DesiredState",
    "KnownStateHandler",
    "LocalJSONKnownStateHandler",
    "LocalYAMLKnownStateHandler",
    "Reconciler",
    "WiringContainer",
    "register_observed_state_handler",
    "register_resource_manager",
]
```

And `src/pylibreconcile/wiring/__init__.py`:

```python
# src/pylibreconcile/wiring/__init__.py
from .container import WiringContainer
from .decorators import (
    register_observed_state_handler,
    register_resource_manager,
)

__all__ = [
    "WiringContainer",
    "register_observed_state_handler",
    "register_resource_manager",
]
```

---

## Files changed (exact list)

**New files:**

- `src/pylibreconcile/wiring/__init__.py`
- `src/pylibreconcile/wiring/container.py`
- `src/pylibreconcile/wiring/decorators.py`
- `tests/wiring/__init__.py`
- `tests/wiring/conftest.py`
- `tests/wiring/container_test.py`
- `tests/wiring/decorators_test.py`
- `tests/wiring/inheritance_test.py`

**Edited files:**

- `src/pylibreconcile/__init__.py` — fix the broken `.core` import;
  add the new exports above. Also add `Change` / `ChangeType` from
  the previously untracked `change.py`.
- `src/pylibreconcile/desired_state/models.py` — **no edits
  required.** The plan does not modify `__init_subclass__`. (See
  Pre-flight observation 7: existing tests in `tests/core_test.py`
  must continue to pass unchanged.)
- `src/pylibreconcile/observed_state/__init__.py` and
  `src/pylibreconcile/resource_manager/__init__.py` — add
  re-exports of `ObservedStateHandler` / `ResourceManager` from
  the corresponding `protocol.py`. Without these, the new
  `WiringContainer` imports fail. (Currently empty files.)

**Committed as-is (no edits):**

- `src/pylibreconcile/change.py` — currently untracked. This plan
  adds it to git history with no modifications. The future
  `DriftPolicy` plan will add `action_performed` to it.
- `src/pylibreconcile/reconciler.py` — completely untouched. The
  pre-existing broken `get_change_set` body stays broken (see
  Pre-flight observation 2). The pre-existing
  `tests/reconciler_test.py` is also out of scope — it's broken in
  the working tree today (passes a `list` where a
  `KnownStateHandler` is expected) and remains broken after this
  plan; fixing it belongs to the Seed 6 reconcile-loop rewrite.
- `tests/core_test.py` — **no edits required.** Existing tests
  must keep passing unchanged. Decorators do not touch
  `DesiredState` internals, so `to_hash()`, dataclass field
  exclusion, and `__init_subclass__` behaviour are all preserved.
- `tests/reconciler_test.py` — **no edits.** The pre-existing
  smoke test (`Reconciler(states)` constructor) is broken in the
  current working tree and stays broken. Out of scope here.
- `docs/context/overview.md` — update the quick-sketch example
  (lines 188-193) to use the new decorator-based wiring instead
  of the obsolete `observed_state_managers={...}` /
  `resource_managers={...}` constructor kwargs. Do NOT touch the
  `Reconciler(...)` constructor kwargs in the sketch — those are
  already inconsistent with the current source and will be fixed
  by the Seed 6 reconcile-loop rewrite.
- `docs/context/glossary.md` — add `WiringContainer`,
  `register_observed_state_handler`, `register_resource_manager`
  entries. Update the `ObservedStateManager` and `ResourceManager`
  entries to mention they are registered per-`DesiredState`-type
  via the new mechanism. Do NOT add `DriftPolicy` (future plan).
- `docs/plans/0002-bootstrap-docs-context.md` — close Seed 1 in
  the "Future plan seeds" section (lines 864-888) — lookup
  mechanism is resolved by this plan. Leave Seeds 3, 6, 7 open
  (those are for the future `DriftPolicy` and reconcile-loop
  plans).
- `CHANGELOG.md` — under `[Unreleased] / Added`, add bullets for
  `WiringContainer` and the two decorators. Do NOT mention
  `DriftPolicy` (future plan).

**Not changed (out of scope):**

- `src/pylibreconcile/core.py` — delete in the `src/` commit (it's
  empty; tracked in git history; deleting from the working tree
  is safe).
- `src/pylibreconcile/observed_state/protocol.py` — unchanged.
- `src/pylibreconcile/resource_manager/protocol.py` — unchanged.
- `src/pylibreconcile/known_state/*` — unchanged.
- `src/pylibreconcile/reconciler.py` — entirely untouched. No
  constructor changes, no new methods, no per-call overrides.
- `pyproject.toml`, `uv.lock`, `Makefile`, `AGENTS.md`,
  `.pre-commit-config.yaml`, `.opencode/rules/*` — no changes needed.
- CI configuration — no changes.

---

## Public API surface (what callers see)

After this plan lands, the public surface adds:

```python
# Container
class WiringContainer:
    _instance: Optional[WiringContainer]  # class attr (singleton marker)

    def __new__(cls) -> WiringContainer: ...
    def register(
        self,
        desired_state_type: type[DesiredState],
        observed_state_handler: Optional[ObservedStateHandler] = None,
        resource_manager: Optional[ResourceManager] = None,
    ) -> None: ...  # raises ValueError if both args are None
    def get(
        self,
        desired_state_type: type[DesiredState],
    ) -> Optional[
        tuple[Optional[ObservedStateHandler], Optional[ResourceManager]]
    ]: ...  # walks MRO; returns None if no wiring exists
    def clear(self) -> None: ...


# Decorators
def register_observed_state_handler(
    instance: ObservedStateHandler,
) -> Callable[[type[DesiredState]], type[DesiredState]]: ...


def register_resource_manager(
    instance: ResourceManager,
) -> Callable[[type[DesiredState]], type[DesiredState]]: ...
```

That is the entire new public surface. Nothing else changes in
this plan.

- `Reconciler.__init__` / `Reconciler.reconcile()` are unchanged.
- `Change` and `ChangeType` are committed as-is (no `action_performed`).
- No new policy module, no new enum.

The next plan (`0005-drift-policy-and-reconciler-validation.md`)
will add `DriftPolicy`, `_validate_wiring_for_settings`, and
`Change.action_performed` on top of this foundation.

---

## Test plan

All tests go under `tests/wiring/` (mirroring `tests/known_state/`).

### `tests/wiring/container_test.py`

Mirror the structure of `tests/known_state/local_test.py`. Each
test **starts with** `WiringContainer().clear()` (either as a
fixture or inline) so the singleton state from previous tests
doesn't leak.

- `test_singleton_returns_same_instance` —
  `WiringContainer() is WiringContainer()`.
- `test_clear_resets_registry` — register, clear, get returns None.
- `test_register_with_observer_only` — register with
  `observed_state_handler`, leave `resource_manager=None`; no
  raise.
- `test_register_with_manager_only` — register with
  `resource_manager`, leave `observed_state_handler=None`; no
  raise.
- `test_register_with_both` — register both; no raise.
- `test_register_with_neither_raises` — register with both `None`;
  raises `ValueError`. Verify message mentions
  `desired_state_type.__name__`.
- `test_get_returns_registered_pair` — register, get returns the
  same pair (identity check on both instances).
- `test_get_returns_none_for_unregistered` — get on an unregistered
  type returns `None`.
- `test_get_walks_mro` — register on a parent, get on a child
  returns the parent's wiring. Three levels deep.
- `test_get_walks_mro_returns_closest_first` — register on both a
  parent and a child (same handler instance key matters: parent
  registered, child registered → child's wins; verify with a
  sentinel attribute).
- `test_clear_then_register_works` — clear between, register
  again, get works.
- `test_register_overwrites` — register twice on the same type;
  second call wins.
- `test_register_pair_merges_partial_registrations` — call
  `WiringContainer()._register_pair(cls, observed=handler)`
  then `_register_pair(cls, manager=rm)`; final entry has both.
- `test_register_pair_first_call_with_only_one_does_not_raise` —
  even though `register(cls)` with both-None raises, going
  through `_register_pair` with only one set succeeds because
  the merge keeps at least one non-None.

### `tests/wiring/decorators_test.py`

- `test_only_observer_decorator_registers_observer_only` — apply
  only `@register_observed_state_handler(...)`. After class
  creation, `WiringContainer().get(cls)` returns
  `(observer, None)`.
- `test_only_manager_decorator_registers_manager_only` — apply only
  `@register_resource_manager(...)`. After class creation,
  `WiringContainer().get(cls)` returns `(None, manager)`.
- `test_both_decorators_register_both` — apply both.
  `(observer, manager)`.
- `test_decorator_order_does_not_matter` — `@register_resource_manager`
  above `@register_observed_state_handler` produces the same
  final entry as the reverse order.
- `test_undecorated_subclass_is_not_registered` — define a plain
  `class X(DesiredState): ...`, `WiringContainer().get(X)` is None.
- `test_decorator_returns_class_unchanged` — the decorator returns
  `cls`; the class is still instantiable and is still a
  dataclass.
- `test_decorator_does_not_add_dataclass_fields` — decorated
  subclass has the same fields as an undecorated equivalent.
  (Decorators do NOT add `ClassVar` markers — see Design §2
  technical correction.)
- `test_decorator_with_explicit_dataclass_still_works` — define
  `@dataclass class X(DesiredState): ...` then decorate. The
  explicit `@dataclass` stays; the wiring still registers. (Mirrors
  the existing `test_desired_state_intermediate_explicit_dataclass`
  pattern in `tests/core_test.py`.)
- `test_decorator_with_inheritance_chain` — decorate parent,
  register on parent; child is not decorated but should inherit
  via MRO walk on `get`.
- `test_decorator_does_not_mutate_class_dict` — the decorator
  must NOT add `_observed_state_handler_instance` /
  `_resource_manager_instance` to the class dict (registration is
  via the container, not via class attributes — see Design §2
  technical correction).

### `tests/wiring/inheritance_test.py`

- `test_one_level_inheritance_walks_mro` — `class A(DesiredState):`
  decorated, `class B(A):` undecorated. `get(B)` returns A's wiring.
- `test_three_level_inheritance_walks_mro` — extend to three
  levels.
- `test_child_decoration_overrides_parent` — both decorated; `get`
  on child returns child's wiring.

### `tests/core_test.py` — no additions, no edits

The existing 363-line `tests/core_test.py` MUST keep passing
unchanged. The implementer should run
`make test-fast tests/core_test.py` after the `src/` commit to
confirm. Adding tests to `core_test.py` is unnecessary here:
this plan does not change `DesiredState` or its `__init_subclass__`
behaviour in any way.

### Test ordering and isolation

`WiringContainer` is a process-wide singleton. **Every test in
`tests/wiring/` MUST call `WiringContainer().clear()` either in a
fixture or at the start of the test body.** Use a
`pytest.fixture(autouse=True)` in `tests/wiring/conftest.py` (new
file) for cleanliness:

```python
# tests/wiring/conftest.py
import pytest
from pylibreconcile import WiringContainer


@pytest.fixture(autouse=True)
def _wiring_container_reset() -> None:
    WiringContainer().clear()
```

Same autouse fixture in `tests/reconciler_test.py` (or extend
`tests/reconciler_test.py` to do it inline). Without this,
`pytest-randomly` ordering or running tests in isolation will
produce false negatives.

### Coverage target

`pyproject.toml` enforces coverage on `src/` (branch + line, see
`pyproject.toml:85-103`). Aim for 100% on the new code. The wiring
container is small enough that 100% is realistic. Exceptions are
explicit `raise NotImplementedError` (excluded by the coverage
config at `pyproject.toml:97`).

---

## Implementation sequence

The implementer should follow this order to keep each commit
landable and `make all` green at every step. **This is the order
the commits land**, not necessarily the order the files are
written — files can be written ahead of time, but `git add` /
`git commit` happens in this order.

### Commit 1 — `feat: add WiringContainer, decorators, and fix import paths`

- **Files:**
  - **New subpackage** `src/pylibreconcile/wiring/` with three
    files: `__init__.py`, `container.py`, `decorators.py`.
  - **New re-exports** in
    `src/pylibreconcile/observed_state/__init__.py` and
    `src/pylibreconcile/resource_manager/__init__.py` (currently
    empty — add `from .protocol import ObservedStateHandler` and
    `from .protocol import ResourceManager` respectively).
  - **Rewrite** `src/pylibreconcile/__init__.py` to fix the
    broken `.core` import (`DesiredState` now comes from
    `.desired_state`), add the new public exports
    (`WiringContainer`, `register_observed_state_handler`,
    `register_resource_manager`), and add `Change` / `ChangeType`
    from the previously untracked `change.py`.
  - **Land untracked file** `src/pylibreconcile/change.py` as-is
    (it's currently sitting in the working tree, uncommitted).
  - **Delete** `src/pylibreconcile/core.py` (empty, tracked in git
    history, safe to remove).
- **NOT edited:** `src/pylibreconcile/desired_state/models.py` —
  no edits to `__init_subclass__` (see technical correction in
  Design §2).
- **NOT edited:** `src/pylibreconcile/reconciler.py` — entirely
  untouched.
- **Verification before commit:**
  `python -c "from pylibreconcile import DesiredState, WiringContainer, register_observed_state_handler, register_resource_manager, Change, ChangeType"`
  succeeds.
- **Run:** `make lint format-check typecheck`. (Tests not required
  yet — the test commit is next. The broken `tests/reconciler_test.py`
  was broken in the working tree before this plan started; it stays
  broken after this commit.)
- **Commit message:**
  `feat(wiring): add WiringContainer singleton and decorator-based registration`

### Commit 2 — `test: cover WiringContainer and decorators`

- **Files:** the new test files listed in "Test plan":
  - `tests/wiring/__init__.py`
  - `tests/wiring/conftest.py` (autouse `WiringContainer().clear()` fixture)
  - `tests/wiring/container_test.py`
  - `tests/wiring/decorators_test.py`
  - `tests/wiring/inheritance_test.py`
- **NOT edited:** `tests/core_test.py`, `tests/reconciler_test.py`,
  or any other existing test file.
- **Verification:** `make test tests/wiring/` passes with full
  coverage on the new code. The pre-existing broken
  `tests/reconciler_test.py` and `tests/core_test.py` should
  either pass (if `make test` was run before the recent
  refactor introduced the import break) or be skipped by an
  `xfail`/`skip` — see "Note on the pre-existing broken test
  suite" below.
- **Commit message:**
  `test(wiring): cover container, decorators, and inheritance`

### Commit 3 — `docs: update context, glossary, plans history, and changelog`

- **Files:**
  - `docs/context/overview.md` — update the quick-sketch example
    (lines 188-193) to use the new decorator-based wiring instead
    of the obsolete `observed_state_managers={...}` /
    `resource_managers={...}` constructor kwargs. Do NOT touch
    the `Reconciler(...)` constructor kwargs in the sketch (out
    of scope here).
  - `docs/context/glossary.md` — add `WiringContainer`,
    `register_observed_state_handler`, `register_resource_manager`
    entries. Update the `ObservedStateManager` and `ResourceManager`
    entries to mention they are registered per-`DesiredState`-type
    via the new mechanism. Do NOT add `DriftPolicy` (future plan).
  - `docs/plans/0002-bootstrap-docs-context.md` — close Seed 1 in
    the "Future plan seeds" section (lines 864-888) — the lookup
    mechanism is resolved by this plan. Leave Seeds 3, 6, 7 open
    (those are for the future `DriftPolicy` and reconcile-loop
    plans).
  - `CHANGELOG.md` — under `[Unreleased] / Added`, add bullets
    for `WiringContainer` and the two decorators. Do NOT
    mention `DriftPolicy` (future plan).
- **Commit message:**
  `docs(wiring): document container and decorators`

### Final verification

After all three commits:

```bash
make all    # lint + format-check + typecheck + security + test
```

Must be green for the new code. The pre-existing broken state
(`tests/reconciler_test.py` passing `Reconciler(states)` where a
`KnownStateHandler` is expected) is a pre-existing issue that
predates this plan; it does not get fixed here. The new wiring
tests must all pass.

---

## Commit plan (formal, per `.opencode/rules/separate-commits.md`)

The project rule is: stage `src/`, `tests/`, and `docs/` as separate
commits; tooling changes are their own commit; Conventional Commits
prefixes required. This plan has **no tooling changes** — all three
commits fall into the three categories.

| # | Prefix | Scope | Files |
|---|---|---|---|
| 1 | `feat(wiring)` | src | `src/pylibreconcile/wiring/{__init__,container,decorators}.py`, `src/pylibreconcile/observed_state/__init__.py`, `src/pylibreconcile/resource_manager/__init__.py`, `src/pylibreconcile/__init__.py`, `src/pylibreconcile/change.py` (landed untracked), `src/pylibreconcile/core.py` (deleted) |
| 2 | `test(wiring)` | tests | `tests/wiring/{__init__,conftest,container_test,decorators_test,inheritance_test}.py` |
| 3 | `docs(wiring)` | docs | `docs/context/overview.md`, `docs/context/glossary.md`, `docs/plans/0002-bootstrap-docs-context.md`, `CHANGELOG.md` |

Three commits, clean scope, Conventional Commits prefixes.

**Note on landing `change.py`:** `change.py` is currently untracked
in the working tree. It must be committed as part of commit 1
because `src/pylibreconcile/reconciler.py:4` imports `Change` and
`ChangeType` from it — without committing `change.py`, the package
won't import. Landing it alongside the wiring fix is a small
bundling concession to keep the package importable. The
alternative (a separate `feat(change): land initial Change /
ChangeType` commit) would split more cleanly but would require
two `src/` commits for what is effectively one importable-package
fix. The implementer can split it if they prefer; the plan does
not mandate the lump.

---

## Pre-flight observations (out of scope for this plan, but the implementer MUST know)

These are real issues spotted while drafting this plan. They are
flagged here so the implementer doesn't get surprised; they are NOT
part of this plan's scope.

1. **`src/pylibreconcile/core.py` is empty (1 byte)** and
   `__init__.py` imports `DesiredState` from it — the test suite
   cannot even import the package today (`make test-fast` errors
   out at collection). The implementer MUST fix the import path as
   part of commit 1 (this plan does that — `__init__.py` switches to
   `from .desired_state import DesiredState`).
2. **`src/pylibreconcile/reconciler.py` has a broken body** — it
   calls `self._known_state_handler.exists(...)`, `.is_match(...)`,
   and `.get_all()`, none of which exist on the
   `KnownStateHandler` protocol. The actual protocol methods are
   `has_key`, `get_all_keys`, `get_value`, `set_value`. **This
   plan does NOT touch the `Reconciler` at all** — the broken
   body stays, and the broken `tests/reconciler_test.py` (which
   passes a `list` to `Reconciler.__init__`) stays broken. Fixing
   the reconcile loop is a separate refactor (Seed 6 — the
   reconcile-loop re-architecture that will *use* the
   `WiringContainer` this plan lands).
3. **`src/pylibreconcile/change.py` is untracked** — the user
   has begun adding `Change` and `ChangeType` but hasn't committed
   it yet. This plan lands it as-is (no `action_performed` field,
   no other modifications). Future `DriftPolicy` plan will add
   `action_performed`.
4. **`src/pylibreconcile/observed_state/__init__.py` and
   `src/pylibreconcile/resource_manager/__init__.py` are empty**.
   The plan's `WiringContainer` imports from them via
   `from ..observed_state import ObservedStateHandler` (and the
   resource_manager equivalent). Those `__init__.py` files MUST
   re-export the protocol classes — otherwise the imports fail.
   The plan **explicitly** lists these in commit 1 (see "Files
   changed"). Mirrors the pattern at
   `src/pylibreconcile/desired_state/__init__.py:1`.
5. **`standards://python/syntax` says "ALWAYS postfix interface
   classes with `Interface`" and "NEVER use Protocol"**, but the
   existing protocols (`ObservedStateHandler`, `ResourceManager`,
   `KnownStateHandler`) are `@runtime_checkable` `Protocol`s, and
   the investigation uses `ObservedStateHandler` and
   `ResourceManager` as their public names. This is a known
   deviation from the syntax standard. **This plan does not change
   the existing protocol classes.** Renaming them is out of scope
   and would be a separate refactor (one that touches every
   concrete handler and every test). Flagged under "Open
   questions" below as a project-wide debt item, not a plan item.
6. **`standards://python/syntax` says "NEVER use `*args` or
   `**kwargs` method signatures"**, but `__init_subclass__(cls, /,
   **kwargs: object)` already uses `**kwargs` (existing code at
   `src/pylibreconcile/desired_state/models.py:7`). This plan does
   not touch that — preserving existing behaviour. Flagged.
7. **`tests/core_test.py:107` already tests
   `@dataclass class ExampleState(DesiredState): id, name`** —
   explicit `@dataclass` on a subclass. This plan does not modify
   `__init_subclass__` (see Design §2), so this test must continue
   to pass unchanged. Verify after commit 1.
8. **`CHANGELOG.md:12-14` is missing `LocalYAMLKnownStateHandler`**
   from the existing bullet (the same pre-existing observation at
   [`0002-bootstrap-docs-context.md:843-846`](../plans/0002-bootstrap-docs-context.md)).
   The implementer should NOT fix it as part of this plan
   (separate commit / PR). Flagged.
9. **Pre-existing broken test suite.** `make test-fast` currently
   errors at collection because `__init__.py` imports `DesiredState`
   from the empty `core.py`. Commit 1 fixes the import path. After
   commit 1 lands, `tests/core_test.py` should pass. But
   `tests/reconciler_test.py` will still fail because it constructs
   `Reconciler(states)` with the wrong argument type (it should be
   `Reconciler(known_state_handler)`). This is a pre-existing
   failure; do NOT fix it as part of this plan. Flagged.

---

## Open questions (for future plans, not blockers for this one)

These are deliberately deferred to a follow-up plan that builds
on top of this one:

1. **`DriftPolicy` enum and `Reconciler._validate_wiring_for_settings`.**
   The investigation's Question 4 lands in a future
   `0005-drift-policy-and-reconciler-validation.md` plan. It will
   add a new `src/pylibreconcile/policy.py` module (or pick a
   different home), a `drift_policy` constructor parameter on
   `Reconciler`, a per-call override on `reconcile()`, and a
   `_validate_wiring_for_settings` method called from `__init__`.
2. **`Change.action_performed`.** The investigation's Question 5.
   Lands in the same future plan as `DriftPolicy`.
3. **`ImportPolicy`.** Future Seed 7. Lands alongside `DriftPolicy`
   in `policy.py` (the same home). Out of scope here.
4. **`WiredResource` pair-wrapper abstraction.** Explicitly deferred
   by the investigation (line 438-442).
5. **`Reconciler` reconcile-loop rewrite (Seed 6).** The future
   plan that *uses* the `WiringContainer` this plan lands.
   Consumes `WiringContainer().get(desired_type)` per-resource.
6. **Async / sync on the protocols.** Future. Sync V1.

These are the natural next steps after this plan lands. They
each deserve their own plan.

Other deferred items:

7. **Should `ObservedStateHandler` and `ResourceManager` be renamed
   to `*Interface` and switched from `Protocol` to `abc.ABC` per
   `standards://python/syntax`?** Project-wide refactor. Out of
   scope here.
8. **Should `WiringContainer` support iteration (`__iter__` or
   `all()`) for use cases like a "list all wired types" debug
   print?** Currently uses `_wiring.items()` internally; a public
   method is a 3-line addition; deferred until a real caller
   needs it.
9. **Should `Reconciler` accept an injected `WiringContainer`
   override (for per-tenant registries)?** The investigation
   (lines 252-258) explicitly deferred this: "the right move is
   *not* to break the singleton but to add a per-`Reconciler`
   *override* surface ... a future-plan seed, not V1."
10. **Should `register_*` decorators validate the instance against
    the protocol at decoration time?** `isinstance(instance,
    ObservedStateHandler)` would catch caller mistakes early. The
    investigation says the decorator layer is presentation and
    shouldn't know about policy. Adding `isinstance` checks is a
    judgment call; the implementer should add them (cheap,
    defensive, aligns with `standards://python/architecture`'s
    encapsulation rule) and flag in the PR. **Recommendation:
    add `isinstance` checks**, raise `TypeError` on mismatch.

---

## Risks and edge cases

- **Singleton + tests.** The `WiringContainer` is a process-wide
  singleton. If the test suite runs in parallel (it does not today —
  `pyproject.toml` does not configure `pytest-xdist`), state leaks
  across tests. Mitigation: the `autouse=True` fixture in
  `tests/wiring/conftest.py`. If parallel tests are added later, the
  fixture is per-test but still per-process; per-test isolation is
  fine because each test runs `clear()` first.
- **Subclassing `WiringContainer`.** The singleton enforcement via
  `__new__` assumes no subclass overrides `__new__`. Documented in
  the class docstring as "do not subclass."
- **Decorator on a non-`DesiredState` class.** The TypeVar bound
  (`type[DesiredState]`) makes mypy catch the misuse, but at
  runtime a caller could pass any class. `__init_subclass__` on
  `DesiredState` is only invoked on `DesiredState` subclasses, so a
  non-subclass would not trigger registration. The decorator
  still calls `WiringContainer()._register_pair(cls, ...)` with
  the non-`DesiredState` class as the key — the registry accepts
  any class. Acceptable; documented in the decorator docstring.
- **Subclassing a `DesiredState` that already has wiring** — the
  decorator runs again on the subclass. If the subclass has
  neither decorator, it inherits via MRO walk on `get`. If the
  subclass has its own decorator, it registers itself separately
  (decorator order matters: applying `@register_resource_manager`
  before `@register_observed_state_handler` on the same subclass
  produces the same final entry as the reverse order, because
  `_register_pair` merges).
- **Deleting `src/pylibreconcile/core.py`** in commit 1 is
  required to keep the import path clean. The file is in git
  history, so deletion is safe. If the user prefers to keep the
  empty file for any reason (e.g., a "stub" intent), use a
  redirect comment instead — but deletion is cleaner.
- **Landing untracked `change.py` as part of commit 1.** Bundling
  a small concession to keep `src/pylibreconcile/reconciler.py:4`
  importable. Alternative: split into a separate `feat(change):
  land initial Change / ChangeType` commit. The plan does not
  mandate the lump.

---

## What this plan does NOT include

- No `DriftPolicy` enum (Question 4 of the investigation — future
  plan).
- No `Reconciler` constructor changes — the `Reconciler` is
  entirely untouched.
- No `Reconciler._validate_wiring_for_settings()` method (Question
  5 of the investigation — future plan).
- No `Reconciler.reconcile()` per-call `drift_policy` override
  (future plan).
- No `Change.action_performed` field (future plan).
- No `ImportPolicy` enum (future Seed 7).
- No `WiredResource` pair-wrapper abstraction.
- No async conversion of the protocols.
- No `Reconciler` reconcile-loop re-architecture (Seed 6 —
  separate refactor that will *use* the `WiringContainer` this
  plan lands).
- No runtime dependency changes (`pyproject.toml` / `uv.lock`
  untouched).
- No CI / GitHub workflow changes.
- No Sphinx doc changes — `docs/sphinx/` is the hosted user docs;
  this plan only updates `docs/context/` (agent-facing).
- No additional KnownState backends (no `BoltDBKnownStateHandler`
  changes; already shipped per `0003-add-boltdb-known-state-handler.md`).
- No fix for the pre-existing broken `tests/reconciler_test.py`
  (separate refactor).

---

## Next step (when implementation starts)

1. **Commit 1** — `feat(wiring): add WiringContainer singleton and
   decorator-based registration`. Write the three new
   `src/pylibreconcile/wiring/*.py` files. Add the re-exports to
   `observed_state/__init__.py` and `resource_manager/__init__.py`.
   Rewrite `src/pylibreconcile/__init__.py` (fix the broken
   `.core` import + add the new public exports + add `Change` /
   `ChangeType` from the untracked `change.py`). Land the
   untracked `change.py`. Delete `core.py`. Run `make lint
   format-check typecheck`. Commit.
2. **Commit 2** — `test(wiring): cover container, decorators, and
   inheritance`. Write all new test files. Run `make test
   tests/wiring/`. Commit.
3. **Commit 3** — `docs(wiring): document container and
   decorators`. Update `docs/context/overview.md`,
   `docs/context/glossary.md`,
   `docs/plans/0002-bootstrap-docs-context.md` (close Seed 1),
   and `CHANGELOG.md`. Run `make docs-strict` to confirm Sphinx
   still builds. Commit.
4. **Final gate** — `make all` from a clean working tree. The
   new code (wiring + tests + docs) must be green. The
   pre-existing broken `tests/reconciler_test.py` may still fail
   — that's pre-existing and out of scope here. Open a PR. **Do
   NOT merge** (per AGENTS.md rule 12; only the human merges).
5. **Final step** — rename this plan file. See next section.

---

## Final step — rename this plan file (only after everything is done)

Once all three implementation commits are landed and `make all` is
green **and** the PR is open, rename `docs/plans/PLAN.md` to follow
the project's zero-padded-numeric filename convention (established
by `0002-bootstrap-docs-context.md` and `0003-add-boltdb-known-state-handler.md`).

Target filename:

```bash
git mv docs/plans/PLAN.md docs/plans/0004-wiring-container-design.md
```

**Important guards (mirrored from `0003-add-boltdb-known-state-handler.md:506-540`):**

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
- **One extra commit for the rename**, separate from the five
  implementation commits, prefixed `chore(plans):`. Example:

  ```bash
  git add -A docs/plans/
  git commit -m "chore(plans): archive completed plan

  Rename docs/plans/PLAN.md to
  docs/plans/0004-wiring-container-design.md after the
  WiringContainer / DriftPolicy work is complete and shipped."
  ```

- **This rename commit is the LAST commit on the branch.** No code,
  test, or doc edits belong in it. If you find yourself wanting to
  fix something while doing the rename, stop — that's a separate
  commit on a different branch / PR.
