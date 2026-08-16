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