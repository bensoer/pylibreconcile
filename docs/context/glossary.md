# Glossary

Terminology used in [`overview.md`](overview.md) and across the
`pylibreconcile` codebase.

## Three states (the core)

- **Desired State** — declared intent; what the caller says should
  exist. Implemented as subclasses of `pylibreconcile.DesiredState`
  (a dataclass base class at `src/pylibreconcile/desired_state/models.py` that
  auto-applies `@dataclass` in `__init_subclass__` and provides a
  `to_hash()` over ordered field values). Stateless — re-reads its
  declarative input on every reconcile pass.
- **Observed State** — fresh read of reality; what the target
  system currently reports. Stateless — re-queried on every
  reconcile pass, typically via API call or DB query. The library
  itself does not observe; the caller wires in the per-type
  components that do (see "Plumbing / wiring").
- **Known State** — the "documented state." Durable record of what the
  Reconciler believes it has written. Persisted across passes via
  `KnownStateHandler`. The *only* stateful piece of the library —
  "the stateful database in an otherwise stateless library."
  Currently a key → string-value store; richer shape is future
  design.

## Roles and operations

- **Reconciler** — the loop that compares the three states and emits
  actions. One `reconcile()` call = one read-compare-emit cycle.
  Async w.r.t. the declaration of Desired State.
- **Reconcile** — a single pass of the Reconciler.
- **Reconcile pass** — one read-compare-emit cycle across all
  resources in scope.

## Actions (what the Reconciler emits)

- **Create** — Desired exists, Observed does not, Known does not.
  Nothing exists yet; build it.
- **Update** — Desired exists, Observed exists, Known exists but
  does not match (per the `is_match` check). We wrote something
  stale; rewrite it via `update(desired)`.
- **Delete** — Desired does not exist, Observed exists, Known
  exists. All three agree the resource should not exist; remove it.
- **Import** — Desired exists, Observed exists, Known does not.
  Reality has it, but the Reconciler has never recorded it. Bring it
  under management per the configured `ImportPolicy`.
- **Drift Detection** — Desired exists, Observed does not, Known
  exists. We wrote it, but reality no longer has it. The reconciler
  notices and either recreates or flags.

## Properties

- **Source of Truth** — the role Desired State plays; the other two
  states are recruited to agree with it.
- **Election / 2/3 Quorum** — the rule by which the Reconciler deduces
  an action from the three states' agreements. Any two agreeing is
  enough to deduce what is needed; the goal is full three-way
  agreement.
- **Idempotent** — repeated reconcile passes produce the same end
  state. Achieved because each pass reads Observed fresh and Known
  reflects the last successful action — a failed action leaves Known
  unchanged, so the next pass retries.
- **Eventual Reconciliation** — borrowed from K8s controllers; the
  guarantee that the system converges to a steady state over time,
  not on a single pass. In `pylibreconcile`, this is achieved by the
  *caller* looping `reconcile()` (since the library itself does not
  ship a scheduler).
- **Dependency Mapping** — emergent, not declared. Enforced via
  failed / skipped states during reconciliation — if resource B
  fails, any resource A that depends on B is skipped or also fails.
- **Durability** — the property that mid-processing failures do not
  leave the system inconsistent. Achieved because Known State is only
  written after a successful action; a failure means Known still
  reflects the pre-attempt state.

## Plumbing / wiring

- **KnownStateHandler** — the Protocol that backs Known State
  persistence. Already implemented with local JSON / YAML / SQLite
  / Azure Blob / AWS S3 backends.
- **ObservedStateManager** — per-`DesiredState`-type component for
  the *observation / comparison* side of Observed State:
  `is_match(desired, known)`, `exists(...)`, and other read-only
  primitives needed by the decision matrix. Does not mutate
  reality. Registered per-`DesiredState`-type via the 
  `@register_observed_state_handler` decorator.
- **ResourceManager** — per-`DesiredState`-type component for the
  *action* side: `create(...)`, `update(...)`, `delete(...)`. The
  only place that mutates reality. Conceptually distinct from
  `ObservedStateManager` so the read and write surfaces can evolve
  independently. Registered per-`DesiredState`-type via the
  `@register_resource_manager` decorator.
- **ImportPolicy** — a configuration setting that controls what the
  Reconciler does when the matrix says IMPORT. Four modes: `auto`
  (auto-import and continue), `warn` (auto-import but include the
  item in the return value so the caller can log it), `reject`
  (raise / fail immediately), `skip` (do nothing, leave the
  resource unmanaged). Placement: constructor default + per-call
  override.
- **ObservedState** — _(deprecated term; the original combined
  read+write role was split into `ObservedStateManager` and
  `ResourceManager`.)_
- **Observer** — _(deprecated term; absorbed into
  `ObservedStateManager`.)_
- **WiringContainer** — singleton DI container that maps each
  `DesiredState` type to its (optional) `ObservedStateHandler`
  and (optional) `ResourceManager`. Tests clear it between cases
  with `WiringContainer().clear()`. Not for production callers.
- **`register_observed_state_handler`** — class decorator that
  binds an `ObservedStateHandler` instance to a `DesiredState`
  subclass. Registers directly with `WiringContainer`.
- **`register_resource_manager`** — class decorator that
  binds a `ResourceManager` instance to a `DesiredState`
  subclass. Registers directly with `WiringContainer`.

## Out-of-scope rows (explicit non-actions)

These rows in the decision matrix are intentional, not missing
behaviour:

- All three present and matching → no-op (converged).
- Desired ✗, Known ✗, Observed ✓ — "phantom observation." Reality
  has something the Reconciler was never asked about. **Out of
  scope.** Analogy: Terraform cannot manage resources not in its
  state file; resources someone else created by hand are
  Terraform's "not my problem."
- Desired ✗, Known ✓, Observed ✗ — stale Known record with no
  Desired backing. **Out of scope** (or potentially GC).
- Desired ✗, Known ✗, Observed ✗ — trivially nothing to do.