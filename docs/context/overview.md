# pylibreconcile — overview

## What it is

`pylibreconcile` is a domain-agnostic Python library for **declarative
reconciliation** — comparing a **Desired State** against an **Observed
State** and a **Known State** to deduce **Create / Update / Delete /
Import / Drift** actions against any API or server. The library
supplies the reconciliation algorithm; you supply the wiring (how
declarative config becomes Desired State, how reality is queried,
where Known State is stored).

## The problem this solves

Every API or server you want to drive declaratively requires the same
reconciliation algorithm — compare what's declared against what exists,
emit Create / Update / Delete, detect drift, support import, recover
from mid-flight failures. The algorithm does not change between use
cases; only the wiring does (declarative input format, existence
check, state storage). Today, every team re-implements this loop from
scratch. `pylibreconcile` is the loop; you write the wiring.

The library's three states are all **wiring points**:

- **Desired State** — declarative input becomes `DesiredState` objects.
- **Observed State** — fresh lookups against the real world (API, DB).
- **Known State** — durable record of what has been written, stored
  via `KnownStateHandler` (already implemented with local JSON /
  YAML, Azure Blob, and AWS S3 backends).

## Audience

**DevOps and platform engineers** building internal automation that
needs to drive an API or server through a declarative interface.

The canonical scenario: you have a declarative configuration (a file,
an API payload, a CRD-style spec) that is meant to *represent* an API
or server configuration. That configuration acts as the user interface
for managing the API or server. The reconciliation algorithm is the
same in every case — only the wiring changes.

**Entry point.** The caller maps their declarative config into one or
more subclasses of `pylibreconcile.DesiredState` (a dataclass base
class — see [`glossary.md`](glossary.md)) and passes them to
`Reconciler(...)` as an `Iterable[DesiredState]`. They also supply,
per `DesiredState` type, an [`ObservedStateManager`](glossary.md#plumbing--wiring)
(read / comparison) and a [`ResourceManager`](glossary.md#plumbing--wiring)
(write / action). Known State storage is picked at construction time
from the existing `KnownStateHandler` backends (local JSON / YAML /
Azure Blob / AWS S3).

The library is for situations where this three-state, three-wiring-
point model fits. If a use case needs bespoke reconciliation logic
that does not fit, this library is not the right tool.

## Mental model

Three first-class states — **Desired State**, **Observed State**,
**Known State** — and the **Reconciler** that converges them.

- **Desired State** is the declared intent: what the caller says
  should exist. Stateless — re-reads its declarative input on every
  reconcile pass. Implemented by extending
  `pylibreconcile.DesiredState`.

- **Observed State** is the fresh read of reality; what the target
  system currently reports. Stateless — re-queried on every
  reconcile pass, typically via API call or DB query. The library
  itself does not observe; the caller wires in the per-type
  components that do.

  The wiring is split across two per-`DesiredState`-type
  components:

  - **`ObservedStateManager`** handles the *observation /
    comparison* side — `is_match(desired, known)`, `exists(...)`,
    and other read-only primitives the decision matrix needs.
    Does not mutate reality.

  - **`ResourceManager`** handles the *action* side —
    `create(...)`, `update(...)`, `delete(...)`. The only place
    that mutates reality.

  The split keeps "is this in the right state?" separate from
  "make it so," so each side can evolve independently. (Exact
  method signatures, return types, and how the Reconciler looks
  up the right component for each resource are still evolving —
  see `docs/plans/`.)

- **Known State** is the durable record of what the Reconciler
  believes it has written. Persisted across passes via
  `KnownStateHandler` — currently a key → string-value store with
  local JSON / YAML / Azure Blob / AWS S3 backends. The *only*
  stateful piece of the library — "the stateful database in an
  otherwise stateless library."

The Reconciler reads all three states per resource, classifies them
against the decision matrix, and emits a Create / Update / Delete /
Import / Drift action (or no-op). The action is chosen by **2/3
quorum**: any two of the three states agreeing is enough to deduce
what is needed. The goal is full three-way agreement.

### Decision matrix

Authoritative table — covers all 2³ = 8 combinations of (Desired,
Observed, Known), with explicit classification of in-scope and
out-of-scope rows.

| Desired | Observed | Known | Action                  | In scope? |
| ------- | -------- | ----- | ----------------------- | --------- |
| ✓       | ✓        | ✓ = D | **No-op** (converged)   | yes       |
| ✓       | ✓        | ✓ ≠ D | **UPDATE**              | yes       |
| ✓       | ✗        | ✗     | **CREATE**              | yes       |
| ✓       | ✗        | ✓     | **DRIFT DETECTION**     | yes       |
| ✓       | ✓        | ✗     | **IMPORT**              | yes       |
| ✗       | ✓        | ✓     | **DELETE**              | yes       |
| ✗       | ✓        | ✗     | **Out of scope** — "phantom observation" — reality has something the Reconciler was never asked about. | no        |
| ✗       | ✗        | ✓     | **Out of scope** — "stale Known record" with no Desired backing. | no        |
| ✗       | ✗        | ✗     | **Trivial no-op** — nothing-to-do. | n/a       |

The "out of scope" rows are not bugs. They are explicit scope
declarations. Analogy: Terraform cannot manage resources not in its
state file; resources someone else created by hand are "not my
problem" for Terraform. Same principle here.

### `reconcile()` is one-pass

Each call performs one read-compare-emit cycle across all resources
in scope and returns enough information for the caller to decide
whether to invoke it again. This unopinionated trigger model lets
callers layer on either **Terraform-style** orchestration (one-shot,
on demand) or **K8s-controller-style** orchestration (continuous
loop, fixed interval, possibly with event-driven shortcuts) on top of
the same library — the caller chooses.

### Why all three exist (the pairing logic)

- Known State is what makes DELETE possible. Without it, when the
  caller removes an item from Desired, the Reconciler has no record
  of what *was* there, so it cannot distinguish CREATE from DELETE.
- Observed State is what makes DRIFT and IMPORT detectable. Its
  `is_match` / `update` surface is what the Reconciler uses to
  navigate the decision matrix and drive reality toward Desired.

### Library / caller boundary

`pylibreconcile` *drives* the reconciliation. It invokes
`ObservedStateManager.is_match(...)` to decide what action the
matrix demands, and invokes `ResourceManager.create(...)` /
`update(...)` / `delete(...)` to actually perform it. The caller
extends the relevant protocols and hands instances to the
`Reconciler`; the library does not expose hooks for the caller to
"step in" mid-pass.

### Error handling

The library is **best-effort**. When one resource's `create` /
`update` / `delete` raises mid-reconcile, the library records the
failure, continues processing the remaining resources, and surfaces
the full picture in the return value.

### Quick sketch

Pseudo-code, no real types, ground for first-time readers:

```python
# pylibreconcile — at a glance

# Caller side: declare intent
class ServerDesired(DesiredState):
    hostname: str
    port: int


# Caller side: wire observation + action
class ServerObservedStateManager:
    def is_match(self, desired, known): ...


class ServerResourceManager:
    def create(self, desired): ...
    def update(self, desired, known): ...
    def delete(self, known): ...


# Hand it all to the library
reconciler = Reconciler(
    desired_states=[ServerDesired(hostname="a", port=80)],
    observed_state_managers={ServerDesired: ServerObservedStateManager()},
    resource_managers={ServerDesired: ServerResourceManager()},
    known_state_handler=LocalJSONKnownStateHandler(Path("state.json")),
    import_policy=ImportPolicy.WARN,
)

# One pass; caller decides when to invoke again
result = reconciler.reconcile()
```

## Inspirations

- **Terraform** — declarative state management.
- **Kubernetes Operators** — controller pattern, eventual
  reconciliation.
- **GitOps** — declarative source-of-truth + reconciliation loop.

**Contrast (not inspiration):** Temporal — uses explicit state
transitions and a dependency graph built from them. `pylibreconcile`
stays async and emergent; the dependency structure is implied by
failed / skipped states rather than declared up front.

## Non-goals

- Not an orchestrator. (It does not run workflows on a schedule or
  trigger jobs on a wall clock.)
- Not a workflow engine. (Steps are not first-class; the loop is.)
- Not a state-machine library. (No transition DSL; transitions emerge
  from the 3-state comparison.)
- Not a domain-specific tool. (The library never knows what it is
  reconciling *against*; the caller plugs that in.)
- Not a scheduler. (How often reconcile passes run is the caller's
  responsibility.)

## Where to find more

The following intentionally do **not** live in this overview because
they have a more authoritative home elsewhere:

- **Version, classifiers, dependencies** — `pyproject.toml` is the
  source of truth.
- **PyPI / Read the Docs URLs** — `README.md` and `pyproject.toml`
  (`[project.urls]`).
- **Implementation status, module map, test layout** — to be added
  in a future `docs/context/current-state.md` (not yet written).
