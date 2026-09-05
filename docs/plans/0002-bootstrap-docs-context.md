# Plan: Bootstrap `docs/context/` (active working plan)

**Status:** drafting. This is the live plan being built out across
iterations. See
[`0001-context-folder-bootstrap.md`](0001-context-folder-bootstrap.md) for
the original brainstorm transcript and source-of-inspiration material.
Locking happens when every section below has concrete, copy-pasteable
prose that a code-worker can follow without further conversation.

**Doc set:** `README.md`, `overview.md`, `glossary.md` — three files
under `docs/context/`. No `current-state.md` in this plan.

## Goal

Give subagents (`code-worker`, `git-maintainer`, `test-reviewer`, and any
future ones) a stable place to read what `pylibreconcile` is, what its
vocabulary means, and what already exists in the repo — so every plan,
refactor, or PR doesn't have to re-derive that from scratch.

## Locked decisions

Carried forward from the brainstorm plus the doc-set call made on this
branch.

1. **`docs/plans/` is narrowly scoped.** Historical record of plans
   (human-written and AI-agent-written), decisions, and tasks. Not
   for project context.
2. **Project context lives under `docs/context/`** — sibling to `docs/plans/`
   and `docs/sphinx/`. Chosen over `architecture/`, `project/`, `about/`,
   `design/` because it matches intent ("background agents need to do the
   job") and leaves room for future context docs without overlapping with
   plans.
3. **Plain filenames, no `0001-` numbering prefix on context docs.**
   e.g. `overview.md`, `glossary.md`. Plain names make it obvious
   what each file is for. (Plan files use a separate
   zero-padded-numeric convention — see the plan file naming
   decision in "Open questions" below.)
4. **Domain-agnostic.** Context docs describe what pylibreconcile **is**,
   not what it will reconcile against or what features it will gain.
5. **Markdown format.** Outside `docs/sphinx/`, so no RST. Consistent with
   `AGENTS.md`, `README.md`, `CHANGELOG.md`.
6. **Doc set is locked at three.** `README.md`, `overview.md`,
   `glossary.md`. No `current-state.md` for now (deferred — not
   needed at this stage), no `architecture.md` (overlaps with
   `current-state.md` at this size), no `testing.md` (premature —
   add later when test conventions harden), no `non-goals.md`
   (stays as a section inside `overview.md`).

## Folder layout after execution

```
docs/
├── context/   # NEW — project context for humans + agents (README, overview, glossary)
├── plans/     # existing — historical record of plans / decisions
└── sphinx/    # existing — published Read the Docs site (RST; user / developer docs)
```

## Scope boundary: context, plans, sphinx

Three documentation roots, three audiences. Keep them clearly
distinct — the boundary is part of what makes each one useful.

### `docs/context/` (this plan's output)

**Audience:** humans reading the repo directly + AI agents working on
the project (per `AGENTS.md`).

**Answers:** what is this project, what does its vocabulary mean, what
exists today. Domain-agnostic. Edit when the project *changes shape*
(new module, renamed term, deprecated dependency).

**Format:** plain Markdown filenames (no `0001-` prefix), no RST.
Parallel to `AGENTS.md`, `README.md`, `CHANGELOG.md`.

**Pattern:** living document. Sub-agents should *read* these on entry
and *update* them when the conceptual model shifts.

### `docs/plans/`

**Audience:** humans + AI agents who need historical or in-flight
plans.

**Answers:** what we are doing next, and what we decided in past
sessions. Each plan is task-shaped and time-bound.

**Format:** zero-padded-numeric filenames (`0001-…md`, `0002-…md`).
Plans are sequential.

**Pattern:** historical record. Brainstorm transcripts become the
"why" record; locked decisions in `PLAN.md` (or successor) become
the "what" record.

### `docs/sphinx/source/`

**Audience:** humans coming to the project via the hosted Read the
Docs site — users, integrators, evaluators. **Not** agents.

**Answers:** tutorials, API reference, install guide, and any other
content aimed at someone who is *using* `pylibreconcile` rather than
*working on it*.

**Format:** RST (Sphinx default), hosted on Read the Docs.

**Pattern:** the published docs site. Owned by the human docs
workflow (release process, CI, RTD deploy). **Intentionally not part
of the agent / repo-reader workflow.**

### Cross-linking rules

- `docs/context/*.md` → `docs/plans/`: yes, when a context doc
  references a decision or task. `plans/` transcripts can reference
  `context/` for vocabulary.
- `docs/context/*.md` → `docs/sphinx/`: sparingly, and only when an
  agent genuinely needs to consult user docs (rare). `README.md` and
  `AGENTS.md` each call this out so the boundary stays visible.
- `docs/sphinx/` → `docs/context/` or `docs/plans/`: the Sphinx site
  is its own world; it does not link into internal planning or
  context.

## Draft prose — `docs/context/overview.md` (B) + glossary weaving (D)

This is the current iteration focus. Each block below will be filled in
during the conversation and locked when the prose is copy-pasteable.
Glossary terms introduced while drafting `overview.md` are also captured
here under section D — once locked, they move into `docs/context/glossary.md`
as a unit so the prose references are stable.

### Source material — user's description (verbatim)

Captured verbatim so the prose below is traceable to the user's words.
This is the foundation for B and D.

> pylibreconcile is meant to be a "reconciliation" library inspired off
> the state management and reconciling mechanics of Terraform, K8s
> Operators and GitOps. It uses the concepts of "Desired State", "Known
> State" and "Observed State" as ways to deduce all desired actions of
> Create, Update and Delete resources, but also to detect drift, support
> importing and have durability if Create, Update or Delete actions fail
> mid-processing. It leans on Kubernetes controller philosophy of
> "eventual reconciliation" — so it is async to the Desired States that
> need to be applied and relies on them failing or skipping to enforce a
> level of dependency mapping. A simpler library called Temporal does
> something similar, but it uses states and controls moving from 1 state
> to the next and thus a dependency graph is made from that. libreconcile
> does this in an async manner.
>
> Using the above mentioned states some logic can be all deduced from it:
>
> - Desired State entry exists, Observed state entry does not exist,
>   Known State entry does not exist — this is a CREATE.
> - Desired State entry exists, Observed state entry exists, Known State
>   entry exists but does not match — this is UPDATE.
> - Desired State does not exist, Observed state entry does exists,
>   Known State does exist — this is a DELETE.
> - Desired State entry exists, Observed state does not exist, Known State
>   does exist — this is DRIFT DETECTION.
> - Desired State exists, Observed state exists, Known State does not
>   exist — this is IMPORT.
>
> This is only a subset of examples but you can see the relationships
> going on in here.
>
> Another way to look at this is that Desired State is the "source of
> truth" and then it has to recruit either the Observed State or Known
> State to agree with it. And that ends up with an election system where
> 2/3 states agreeing is enough to deduce the action that is needed.
>
> The action needed is then always in the goal of reconciliation. Getting
> the Desired, Known and Observed States to all agree with each other.

### Structural extraction (derived from the source material)

The user's description breaks into five load-bearing pieces. Each one
maps to a block in `overview.md` or to a glossary term.

1. **Three first-class states, not two.** `Desired State`, `Known State`,
   `Observed State`. **This is a major update from the original brainstorm,
   which only had two.** Any `overview.md` and `glossary.md` draft must
   treat all three as peers.

2. **Inspirations.** Terraform, K8s Operators, GitOps. Plus Temporal as a
   *similar-but-different* reference (state transitions vs. 3-state
   agreement + async). Temporal belongs in `overview.md` as a contrast,
   not as an inspiration.

3. **Capabilities derived from the 3-state model.**
   - Deduce Create / Update / Delete actions.
   - Detect drift (when Desired and Known agree but reality diverges).
   - Import (when reality has a resource but Known State has never
     recorded one).
   - Durability across mid-processing failures.

4. **Design properties.**
   - **Eventual reconciliation** — borrowed from Kubernetes controllers.
   - **Async** relative to the declaration of Desired States.
   - **Dependency mapping emerges** from failed / skipped states, not from
     an explicit graph.
   - **2/3 quorum** — any two of the three states agreeing is enough to
     deduce the action.

5. **Decision matrix (canonical example).** The five cases the user listed
   are not exhaustive of 2³ = 8 — the all-three-agree case (no-op) and
   certain pathological cases are implicit. Whether the matrix lives in
   `overview.md` (as a mental-model anchor) or `current-state.md` (as a
   behaviour spec) is a pending decision.

### Working decision matrix (canonical artifact)

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
| ✗       | ✗        | ✓     | **Out of scope** — "stale Known record" with no Desired backing. (May warrant GC; tracked in D-Q12.) | no        |
| ✗       | ✗        | ✗     | **Trivial no-op** — nothing-to-do. | n/a       |

The "out of scope" rows are not bugs. They are explicit scope
declarations. Analogy: Terraform cannot manage resources not in its
state file; resources someone else created by hand are "not my
problem" for Terraform. Same principle here.

### B.1 Elevator pitch

`pylibreconcile` is a domain-agnostic Python library for **declarative
reconciliation** — comparing a **Desired State** against an **Observed
State** and a **Known State** to deduce **Create / Update / Delete /
Import / Drift** actions against any API or server. The library
supplies the reconciliation algorithm; you supply the wiring (how
declarative config becomes Desired State, how reality is queried,
where Known State is stored).

### B.2 Problem statement

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

### B.3 Audience

**DevOps and platform engineers** building internal automation that
needs to drive an API or server through a declarative interface.

The canonical scenario: you have a declarative configuration (a file,
an API payload, a CRD-style spec) that is meant to *represent* an API
or server configuration. That configuration acts as the user interface
for managing the API or server. The reconciliation algorithm is the
same in every case — only the wiring changes.

**Entry point.** The caller maps their declarative config into one or
more subclasses of `pylibreconcile.DesiredState` (a dataclass base
class — see `current-state.md`) and passes them to `Reconciler(...)`
as an `Iterable[DesiredState]`. They also supply, per
`DesiredState` type, an `ObservedStateManager` (read / comparison)
and a `ResourceManager` (write / action). Known State storage is
picked at construction time from the existing `KnownStateHandler`
backends (local JSON / YAML / Azure Blob / AWS S3).

The library is for situations where this three-state, three-wiring-
point model fits. If a use case needs bespoke reconciliation logic
that does not fit, this library is not the right tool.

### B.4 Mental model

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
  up the right component for each resource are future-plan design
  surface — see "Future plan seeds.")

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

**`reconcile()` is one-pass.** Each call performs one
read-compare-emit cycle across all resources in scope and returns
enough information for the caller to decide whether to invoke it
again. This unopinionated trigger model lets callers layer on either
**Terraform-style** orchestration (one-shot, on demand) or
**K8s-controller-style** orchestration (continuous loop, fixed
interval, possibly with event-driven shortcuts) on top of the same
library — the caller chooses.

**Why all three exist (the pairing logic):**
- Known State is what makes DELETE possible. Without it, when the
  caller removes an item from Desired, the Reconciler has no record
  of what *was* there, so it cannot distinguish CREATE from DELETE.
- Observed State is what makes DRIFT and IMPORT detectable. Its
  `is_match` / `update` surface is what the Reconciler uses to
  navigate the decision matrix and drive reality toward Desired.

**Library / caller boundary.** `pylibreconcile` *drives* the
reconciliation. It invokes `ObservedStateManager.is_match(...)` to
decide what action the matrix demands, and invokes
`ResourceManager.create(...)` / `update(...)` / `delete(...)` to
actually perform it. The caller extends the relevant protocols and
hands instances to the `Reconciler`; the library does not expose
hooks for the caller to "step in" mid-pass. This keeps the contract
simple and the library's behaviour predictable. (Future expansion to
support caller-driven integration modes is parked as architectural
room to grow — see Future plan seeds Seed 1.)

**Error handling.** The library is **best-effort**. When one
resource's `create` / `update` / `delete` raises mid-reconcile, the
library records the failure, continues processing the remaining
resources, and surfaces the full picture in the return value. There
is no built-in fail-fast mode in V1; one can be added later behind a
caller-controlled configuration knob (see Future plan seeds Seed 6).

**Quick sketch.** Pseudo-code, no real types, ground for first-time
readers:

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

### B.5 Inspirations / reference designs

- **Terraform** — declarative state management.
- **Kubernetes Operators** — controller pattern, eventual
  reconciliation.
- **GitOps** — declarative source-of-truth + reconciliation loop.

**Contrast (not inspiration):** Temporal — uses explicit state
transitions and a dependency graph built from them. `pylibreconcile`
stays async and emergent; the dependency structure is implied by
failed / skipped states rather than declared up front.

### B.6 Non-goals

- Not an orchestrator. (It does not run workflows on a schedule or
  trigger jobs on a wall clock.)
- Not a workflow engine. (Steps are not first-class; the loop is.)
- Not a state-machine library. (No transition DSL; transitions emerge
  from the 3-state comparison.)
- Not a domain-specific tool. (The library never knows what it is
  reconciling *against*; the caller plugs that in.)
- Not a scheduler. (How often reconcile passes run is the caller's
  responsibility — see D-Q7.)

### B.7 Exclusions

Things that intentionally do NOT appear in `overview.md` because they
already live elsewhere:

- Version status → `pyproject.toml` (`project.version`, classifiers).
- Dependency list → `pyproject.toml` (`[project] dependencies`).
- PyPI / RTD URLs → `README.md` + `pyproject.toml` (`[project.urls]`).

## D. Glossary — terms that came up while drafting overview.md

Captured inline. Once locked, these move verbatim into
`docs/context/glossary.md` so the prose above can reference them by
name without ambiguity.

### Three states (the core)

- **Desired State** — declared intent; what the caller says should
  exist. Implemented as subclasses of `pylibreconcile.DesiredState`
  (a dataclass base class at `src/pylibreconcile/core.py:6` that
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
  design (Future plan seeds Seed 2).

### Roles and operations

- **Reconciler** — the loop that compares the three states and emits
  actions. One `reconcile()` call = one read-compare-emit cycle.
  Async w.r.t. the declaration of Desired State.
- **Reconcile** — a single pass of the Reconciler.
- **Reconcile pass** — one read-compare-emit cycle across all
  resources in scope.

### Actions (what the Reconciler emits)

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
  notices and (TBD — see Future plan seeds Seed 3) either recreates
  or flags.

### Properties

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
  ship a scheduler — see B.6 non-goals).
- **Dependency Mapping** — emergent, not declared. Enforced via
  failed / skipped states during reconciliation — if resource B
  fails, any resource A that depends on B is skipped or also fails.
- **Durability** — the property that mid-processing failures do not
  leave the system inconsistent. Achieved because Known State is only
  written after a successful action; a failure means Known still
  reflects the pre-attempt state.

### Plumbing / wiring

- **KnownStateHandler** — the Protocol that backs Known State
  persistence. Already implemented with local JSON / YAML / Azure
  Blob / AWS S3 backends.
- **ObservedStateManager** — per-`DesiredState`-type component for
  the *observation / comparison* side of Observed State:
  `is_match(desired, known)`, `exists(...)`, and other read-only
  primitives needed by the decision matrix. Does not mutate
  reality.
- **ResourceManager** — per-`DesiredState`-type component for the
  *action* side: `create(...)`, `update(...)`, `delete(...)`. The
  only place that mutates reality. Conceptually distinct from
  `ObservedStateManager` so the read and write surfaces can evolve
  independently. (Interface design is future-plan surface — see
  "Future plan seeds.")
- **ImportPolicy** — a configuration setting that controls what the
  Reconciler does when the matrix says IMPORT. Four modes: `auto`
  (auto-import and continue), `warn` (auto-import but include the
  item in the return value so the caller can log it), `reject`
  (raise / fail immediately), `skip` (do nothing, leave the
  resource unmanaged). V1 placement: constructor default + per-call
  override (D-Q16).
- **ObservedState** — _(deprecated term; the original combined
  read+write role was split into `ObservedStateManager` and
  `ResourceManager`.)_
- **Observer** — _(deprecated term; absorbed into
  `ObservedStateManager`.)_

### Out-of-scope rows (explicit non-actions)

These rows in the decision matrix are intentional, not missing
behaviour:

- All three present and matching → no-op (converged).
- Desired ✗, Known ✗, Observed ✓ — "phantom observation." Reality
  has something the Reconciler was never asked about. **Out of
  scope.** Analogy: Terraform cannot manage resources not in its
  state file; resources someone else created by hand are
  Terraform's "not my problem."
- Desired ✗, Known ✓, Observed ✗ — stale Known record with no
  Desired backing. **Out of scope** (or potentially GC; see D-Q12).
- Desired ✗, Known ✗, Observed ✗ — trivially nothing to do.

## D. Resolved design questions

### D-Q1 — Observed vs. Known State — RESOLVED

- **Known State** is the "documented state." Durable. Lives across
  reconcile passes. Stored via `KnownStateHandler`. The only stateful
  piece of the library.
- **Observed State** is fresh lookups on every reconcile pass,
  *plus* the wiring that performs the writes (Create / Update /
  Delete). Stateless per-pass. Typically API calls or DB queries.
  Does *not* persist. The library does not know *how* this happens;
  the caller wires it in via the per-type `ObservedState` component.

**Why Known State exists:** without it, when the caller removes an
item from Desired, the Reconciler has no record of what *was* there,
so it cannot distinguish CREATE from DELETE.

**Why Observed State exists:** it answers "does the thing actually
exist in the real world right now, and if not / wrong, can I fix
it?" — the comparison against Known and Desired surfaces drift and
import; the `update` method is what actually drives reality toward
Desired.

**Implication:** the four existing `KnownStateHandler` backends (local
JSON / YAML / Azure / AWS) are correct *for Known State* but say
nothing about how Observed State is wired. That wiring is new design
surface.

### D-Q5 — Observed State component shape — RESOLVED via conceptual split

The original framing had a single component doing both read-side
(`is_match`) and write-side (`update`) work. That mixed two
responsibilities — observation vs. action — making each side harder
to evolve independently. The conceptual split:

- **`ObservedStateManager`** — per-`DesiredState`-type component
  for the *observation / comparison* side. Read-only.
- **`ResourceManager`** — per-`DesiredState`-type component for the
  *action* side. The only place that mutates reality.

The exact method signatures, return types, and lookup mechanism for
both components are deferred to a future plan (see Future plan
seeds, Seed 1).

### D-Q6 — Per-type vs. global wiring — RESOLVED

**Per-`DesiredState`-type.** Both `ObservedStateManager` and
`ResourceManager` are supplied one-per-type, so different
`DesiredState` types can target different surfaces. (Lookup
mechanism — registry, decorator, convention — is future-plan
surface, Seed 1.)

### D-Q7 — Reconciliation trigger — RESOLVED

`pylibreconcile` ships **one-pass semantics**: each `reconcile()`
call is one read-compare-emit cycle. The caller decides whether to
invoke it again. This unopinionated trigger model supports both:

- **Terraform-style** orchestration — one-shot, on demand, the
  caller drives when reconciliation happens.
- **K8s-controller-style** orchestration — the caller wraps
  `reconcile()` in a continuous loop (interval, event-driven, or
  both).

**Side effect:** the return value of `reconcile()` matters. It must
formalize enough information for the caller to decide whether to
continue (e.g., failures, drift surfaces, in-flight imports). The
exact shape is future design — see D-Q17.

**Implication for non-goals:** "not a scheduler" stays in B.6. The
library does not ship a loop, an interval, or an event source.

### D-Q8 — Declarative input entry point — RESOLVED

The user extends `pylibreconcile.DesiredState` (a dataclass base
class at `src/pylibreconcile/core.py:6`) and passes the resulting
subclass instances to `Reconciler(desired_states)` as
`Iterable[DesiredState]`. The library does not parse files, decode
formats, or read process state — the caller maps their declarative
config (file, API payload, CRD spec, anything) into `DesiredState`
objects before handing them off.

**Open:** the user is debating whether to add a `DesiredStateManager`
interface that wraps this. For now, the entry point is the direct
`Reconciler(desired_states)` constructor. Future design surface.

### D-Q9 — Import behaviour — RESOLVED

The user wants an `ImportPolicy` setting with four modes:

- **`auto`** — auto-import and continue. After import, the resource
  falls under D, O, K all true and is managed.
- **`warn`** — same as `auto` but include the imported item in the
  return value so the caller can log / report it.
- **`reject`** — raise / fail immediately on import detection.
- **`skip`** — do nothing, leave the resource unmanaged, continue.

### D-LB1 — Library / caller boundary — RESOLVED

**V1: the library drives.** `pylibreconcile` invokes
`ObservedStateManager` and `ResourceManager` itself; the caller
extends the relevant protocols, hands instances to `Reconciler`,
and the library runs the loop without exposing mid-pass hooks.

**Future:** the user noted that "we may expand the library in the
future to support multiple ways of integration" — i.e. caller-driven
modes are valid future work. The V1 architecture should leave room
for that (the protocols are the seam). Tracked under Future plan
seeds Seed 1.

### D-LB2 — Error handling philosophy — RESOLVED

**V1: best-effort.** When one resource's action fails mid-pass, the
library records the failure, continues processing the remaining
resources, and surfaces the full picture in the `reconcile()` return
value. There is no built-in fail-fast mode in V1.

**Future:** a caller-controlled knob (configurable per Reconciler,
hybrid best-effort / fail-fast) is a clean growth path. Tracked
under Future plan seeds Seed 6.

### D-LB3 — Examples in `overview.md` — RESOLVED

`overview.md` will include a short pseudo-code sketch (~15 lines)
showing the caller extending `DesiredState`, implementing
`ObservedStateManager` and `ResourceManager`, and handing the whole
package to `Reconciler`. Grounds the mental model for first-time
readers without dragging the doc into implementation specifics.

**Note:** deeper, runnable examples belong in `docs/sphinx/` (user
documentation), not in `docs/context/`. Any future `examples.md`
should live under `docs/sphinx/source/` as part of the Sphinx user
guide.

### D-Q16 — `ImportPolicy` placement — RESOLVED at V1

**V1: constructor default + per-call override.**
`Reconciler(..., import_policy=ImportPolicy.WARN)` sets the default;
`reconciler.reconcile(import_policy=ImportPolicy.AUTO)` overrides per
pass. This gives the caller the simple default and the escape hatch
without committing to per-type or per-resource plumbing.

**Future:** as the library grows and the number of configuration
knobs grows, the user expects settings to land in a layered /
composable place. Per-type, per-resource, and richer composition
options are future expansion. Tracked under Future plan seeds Seed 7.

### D-Q17 — `reconcile()` return shape — RESOLVED at V1

**V1 (in `overview.md`): abstract.** `reconcile()` "returns enough
information for the caller to decide whether to invoke it again."
The concrete shape is not locked here.

**Future:** the actual return type (per-resource outcome list,
aggregate counts, error reasons, etc.) will be nailed down in a
later plan. V1 framing should not over-promise. Tracked under
Future plan seeds Seed 6.

## Other context docs (deferred)

### `docs/context/current-state.md` — DEFERRED

Module-by-module status table of `src/pylibreconcile/`, plus Sphinx and
tests status, plus tooling snapshot. **Not in this plan.** Re-decide
later whether to add; the conceptual overview does not require it.

## `docs/context/README.md` (final content)

```markdown
# Project Context

This folder holds background context for `pylibreconcile` — what the
project is, what its vocabulary means, and how it fits into the
broader ecosystem. It is intended for **humans reading the repo
directly**; AI agents working on the project are pointed here from
[`../../AGENTS.md`](../../AGENTS.md) instead.

These documents describe **what the project is**, not what it will do
next. Direction and decisions live in
[`docs/plans/`](../plans/).

## Reading order

If you're new to the project, read in this order:

1. [`glossary.md`](glossary.md) — the vocabulary used here and across
   the codebase (Desired State, Known State, Reconciler, etc.).
2. [`overview.md`](overview.md) — what `pylibreconcile` is and isn't
   (the three-state mental model, audience, inspirations, non-goals).

## Contents

- [`glossary.md`](glossary.md) — terminology reference.
- [`overview.md`](overview.md) — conceptual overview of the project.

## Living documents

Edit these files when the project changes shape — a new vocabulary
term, a renamed concept, or a new non-goal. Implementation details
and "what's next" do not belong here.

## Cross-links

- [`docs/plans/`](../plans/) — historical record of plans and
  decisions.
- [`docs/sphinx/`](../sphinx/) — the published Read the Docs site;
  root for hosted **user / developer documentation** (tutorials, API
  reference, install guide). Sphinx is **not** where this folder's
  audience goes — readers of `docs/context/` are humans reading the
  repo directly, and `docs/sphinx/` is for users coming to the
  project via the hosted docs.
```

## AGENTS.md patch (final wording)

### Patch 1 — Insert "Project Context" block

**Location:** after `## Project Summary`, before `## Setup Commands`.

```markdown
## Project Context

Before working on this project, read the context documents in
[`docs/context/`](docs/context/), in this order:

1. [`glossary.md`](docs/context/glossary.md) — the vocabulary used in
   `overview.md` and across the codebase. Read this first so the
   mental model below lands on familiar terms.
2. [`overview.md`](docs/context/overview.md) — what `pylibreconcile`
   is and isn't (the three-state mental model, audience,
   inspirations, non-goals).
3. [`README.md`](docs/context/README.md) — index of the context
   folder. More useful for human readers than for agents.

These describe **what the project is**, not what it will do next.
Direction and decisions live in [`docs/plans/`](docs/plans/).

`docs/context/` is the agent-facing documentation root. The sibling
[`docs/sphinx/`](docs/sphinx/) is the hosted user / developer
documentation root (Read the Docs; tutorials, API reference, install
guide) — it is **not** where agent documentation goes and agents do
not normally need to consult it.
```

### Patch 2 — Update `## Code Layout` tree

**Location:** inside `## Code Layout`, replace the `docs/` block:

```diff
 ├── docs/
-│   └── sphinx/                  # Sphinx root
+│   ├── context/                 # NEW — project context for humans + agents (README, overview, glossary)
+│   ├── plans/                   # historical record of plans / decisions (humans + agents)
+│   └── sphinx/                  # Sphinx root (hosted user / developer docs; not for agents)
 │       ├── source/
 │       │   ├── conf.py          # Sphinx config (RTD theme, MyST, autodoc)
 │       │   ├── index.rst        # master doc
 │       │   ├── installation.rst
 │       │   ├── usage.rst
 │       │   ├── api.rst
 │       │   ├── changelog.rst    # includes ../../../CHANGELOG.md
 │       │   ├── _static/
 │       │   └── _templates/
 │       └── build/               # generated, gitignored
```

### Out of scope for this patch

- The broken AGENTS.md link at rule 11 (`.agents/rules/separate-commits.md`
  → `.opencode/rules/separate-commits.md`) is a separate bug and should
  not be bundled with the context-folder commit. Captured under
  "Pre-flight observations" below.

## Commit plan (per `.opencode/rules/separate-commits.md`)

- **Commit 1 (`docs:`)** — add `docs/context/` and the three files
  (`README.md`, `overview.md`, `glossary.md`).
- **Commit 2 (`chore(agents):`)** — patch `AGENTS.md` with the
  "Project Context" block and the Code Layout tree update.

Two commits, clean scope, Conventional Commits prefixes.

## Pre-flight observations (out of scope for this plan)

These are real issues spotted while drafting this plan, but they are
not part of the context-folder work. They would have lived in
`current-state.md` if that file existed; since it does not, they
stay here in `PLAN.md` so a future plan can pick them up.

- **`CHANGELOG.md` gap.** `[Unreleased]` lists
  `LocalJSONKnownStateHandler`, `AzureStorageKnownStateHandler`, and
  `AWSS3KnownStateHandler` but omits `LocalYAMLKnownStateHandler` —
  also implemented, exported, and tested.
- **Stale `hello()` references.** `README.md:16` and
  `docs/sphinx/source/usage.rst:6` both reference
  `pylibreconcile.hello()`, which is not exported from
  `src/pylibreconcile/__init__.py`. Initial scaffolding debris.
- **Broken AGENTS.md link.** `AGENTS.md:235` (rule 11) points at
  `.agents/rules/separate-commits.md`, but the actual file lives at
  `.opencode/rules/separate-commits.md`. Separate fix; do not bundle
  into the AGENTS.md commit in this plan.

## Future plan seeds

These topics surfaced during this plan's drafting but were
deliberately left at the conceptual level. They are **not next steps
to work on** — but when a future plan session tackles any of them,
the notes here give that planner the context they need without
having to re-derive from scratch.

### Seed 1 — `ObservedStateManager` + `ResourceManager` protocol design

**Status:** **closed** by the wiring plan
(`docs/plans/PLAN.md`). Lookup mechanism: two decorators
(`@register_observed_state_handler` and `@register_resource_manager`)
register handler instances with a singleton `WiringContainer`
(`src/pylibreconcile/wiring/`). Per-type wiring is resolved via MRO
walk on `WiringContainer.get()`. Remaining open items (sync/async,
richer object shapes) deferred to future plans.

**Original status:** conceptual split confirmed (read side / write side);
interface TBD.

**Discussion summary:** the original framing had a single component
doing both `is_match` (read) and `update` (write). That mixed two
responsibilities — observation vs. action — making each side harder
to evolve independently. The conceptual split is now:

- `ObservedStateManager` — read / comparison / existence checks.
- `ResourceManager` — create / update / delete (the only mutators).

**Resolved by PLAN.md:**
- Lookup mechanism — `WiringContainer` singleton with
  `@register_observed_state_handler` / `@register_resource_manager`
  decorators.
- Method signatures — defined by the `ObservedStateHandler` and
  `ResourceManager` protocols at
  `src/pylibreconcile/observed_state/protocol.py` and
  `src/pylibreconcile/resource_manager/protocol.py`.

**Still open (deferred):**
- Sync vs. async — should methods be `def` or `async def`? Sync V1.
- Return types — what they encode (success? new Known State value?
  error info?).

### Seed 2 — KnownState value shape

**Status:** current implementation is key → string-value (with
base64 encoding on disk for binary safety). Richer shape open.

**Discussion summary:** the existing `KnownStateHandler` Protocol
treats Known State as a flat key-value store of strings. The richer
shape ("object vs. single key") is still TBD. This plan describes
the *current* shape; a future plan will decide whether to expand to
a richer object.

**Open in this seed:**
- Object shape (if any) — what fields? Nested? Typed?
- Comparison semantics — does `is_match` compare the whole object
  or specific fields?
- Encoding — stays base64-on-disk-string, or migrates to JSON /
  YAML at the Known State layer?

**Discussion source:** D-Q15.

### Seed 3 — Drift behaviour

**Status:** decision matrix says DRIFT (D = ✓, O = ✗, K = ✓); the
Reconciler's response is open.

**Open in this seed:**
- Auto-recreate (`update(desired)` and let the underlying API
  recreate)?
- Flag and let the caller decide (return value contains the drift)?
- Surface as a distinct event type?
- Hybrid?

**Discussion source:** D-Q10.

### Seed 4 — Dependency declaration

**Status:** "failed / skipped states enforce a level of dependency
mapping" — but how that mapping is declared is open.

**Open in this seed:**
- Declared (caller says "resource A depends on resource B")?
- Emergent (A fails → B fails because B's state changed)?
- If declared, syntax (a field on `DesiredState`? a separate
  dependency map?).

**Discussion source:** D-Q11.

### Seed 5 — Stale Known record GC

**Status:** the out-of-scope row "Desired ✗, Known ✓, Observed ✗"
is not currently handled. Is it GC, or do we keep ignoring it?

**Open in this seed:**
- Pure ignore (current implicit behaviour).
- Periodic GC pass that detects and removes.
- Lazy GC (remove on next access).

**Discussion source:** D-Q12.

### Seed 6 — Reconciler return shape

**Status:** V1 is abstract ("enough information for the caller to
decide whether to invoke `reconcile()` again"). Concrete shape is
future work.

**Open in this seed:**
- Per-resource outcome list (`list[ReconcileResult]` with
  `{resource, action, status, error?}`) vs. aggregate summary.
- What fields encode failures, drift surfaces, in-flight imports.
- Always returned, or only when there's something to report.
- Likely also: configuring fail-fast mode (D-LB2 growth path).

**Discussion source:** D-Q17, D-LB2.

### Seed 7 — ImportPolicy placement (and broader configuration layering)

**Status:** V1 is constructor default + per-call override. As the
number of configuration knobs grows, the user expects a layered /
composable configuration story.

**Open in this seed:**
- Per-`DesiredState`-type policy.
- Per-resource override.
- Composable config object (constructor accepts a single config
  dataclass that bundles defaults).
- Where future knobs (error handling mode, retry policy,
  concurrency, etc.) live in this layering.

**Discussion source:** D-Q16.

### Seed 8 — `DesiredStateManager` interface (potential addition)

**Status:** user is debating whether to add a `DesiredStateManager`
interface that wraps the current "extend `DesiredState`, hand
`Iterable[DesiredState]` to `Reconciler`" pattern.

**Open in this seed:**
- Do we need a manager at all, or is the direct constructor enough?
- If yes, what does it own — config, ObservedStateManager /
  ResourceManager lookup, lifecycle?
- Backwards compatibility with the direct constructor.

**Discussion source:** D-Q8 (entry point).

## Open questions (pending)

- **Q4 — Glossary scope.** Will close when the final `glossary.md`
  prose is locked (the draft in D below has ~24 terms; the final
  glossary copy will mirror them).
- **Q5 — Plan file naming.** **CLOSED.** Zero-padded numeric prefix
  on plan files (e.g. `0001-context-folder-bootstrap.md`,
  `0002-…md`) is the convention going forward. The original
  brainstorm file at `0001-…` stays as the historical record.
- **Q6 — Overview exclusions.** **CLOSED.** B.7 list (version,
  dependency list, PyPI / RTD URLs) is complete; nothing else
  needs excluding from `overview.md`.
- **Q2 — `current-state.md` depth.** **MOOT.** `current-state.md`
  is deferred (not in the V1 doc set). Revisit when / if it is
  reintroduced.

### Parking lot (not asked yet, possibly worth one round)

- **D-LB5 — Glossary coverage of K8s / Terraform idioms.** The
  overview leans on "controller loop," "declarative state," "source
  of truth" borrowed from those ecosystems. Worth a one-paragraph
  callout that `pylibreconcile` is borrowing the *patterns*, not
  the implementation (i.e., we are not K8s, we are not Terraform)?
- **D-LB6 — `to_hash()` placement.** _(resolved)_ Brief mention
  in the DesiredState glossary entry covers it; fuller detail
  lives in `current-state.md` if / when that file exists.

(These are not blockers; flagging as things we may want to touch on
when we finalise `glossary.md`.)

## What this plan does NOT include

- Any code changes.
- Any actual documentation file creation yet (the context docs
  themselves are not written — they are drafted in `PLAN.md` and the
  implementer will copy them to `docs/context/`).
- Any AGENTS.md edits yet (the patch wording is locked above but
  still needs to be applied by the implementer).
- Any new dependencies, tooling, or release-process changes.
- Detailed interface design for `ObservedStateManager`,
  `ResourceManager`, `ImportPolicy`, `reconcile()` return shape, or
  KnownState value shape — these are Future plan seeds above and
  belong in their own plans.
- A `current-state.md` file. Deferred.

## Next step (when implementation starts)

1. Copy the drafted prose from this plan into the three target
   files (`docs/context/README.md`, `docs/context/overview.md`,
   `docs/context/glossary.md`).
2. Apply the two AGENTS.md patches (Project Context block + Code
   Layout tree).
3. Land the two commits per "Commit plan."
