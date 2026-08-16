# AGENTS.md

Operating instructions for AI agents and human contributors working in this
repository. Anything that is *required* for the project to work — packaging,
dependency resolution, lockfile, etc. — is in `pyproject.toml`. This file
documents conventions, commands, and rules so agents can be effective without
re-discovering them.

## Project Summary

`pylibreconcile` is a Python library for reconciling data against reference
sources. It is published to PyPI and documented on Read the Docs.

- **Language**: Python `>=3.12`
- **Package manager / build tool**: `uv` (Astral)
- **Build backend**: `hatchling`
- **Source layout**: `src/pylibreconcile/` (src layout)
- **Test layout**: `tests/`
- **Docs**: Sphinx + Read the Docs theme, sources in `docs/sphinx/source/`

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

## Setup Commands

**The Makefile is the only entry point for running tools.** All build, test,
lint, format, typecheck, security, docs, and publish commands are routed
through `make`. Do not invoke `uv`, `ruff`, `mypy`, `bandit`, `pip-audit`,
`pytest`, or `sphinx-build` directly in scripts, CI, skills, agent prompts,
or human prose — use the `make` targets below. This keeps tooling
version-pinned and uniform across humans, agents, and CI.

The only raw `uv` invocations permitted are the two project-mutation
commands `uv add` and `uv lock` (which mutate `pyproject.toml` /
`uv.lock`, not run a tool). For regenerating the lockfile prefer `make
lock`.

| Target              | What it does                                                  |
| ------------------- | ------------------------------------------------------------- |
| `make help`         | List all targets                                               |
| `make install`      | `uv sync --all-groups` — install all deps (runtime + dev + docs) |
| `make sync`         | Alias for `install`                                            |
| `make lock`         | `uv lock` — refresh the lockfile                              |
| `make lint`         | Run `ruff check`                                               |
| `make format`       | Run `ruff format` (writes changes)                            |
| `make format-check` | Run `ruff format --check` (CI mode, no changes)                |
| `make typecheck`    | Run `mypy`                                                    |
| `make security`     | Run `bandit -r src -ll` then `pip-audit`                       |
| `make test`         | Run `pytest` with coverage (XML + HTML)                       |
| `make test-fast`    | Run `pytest` without coverage                                  |
| `make docs`         | Build Sphinx HTML into `docs/sphinx/build/html`               |
| `make docs-strict`  | Build Sphinx HTML with `-W --keep-going` (warnings as errors) |
| `make docs-clean`   | Remove `docs/sphinx/build/`                                    |
| `make build`        | Build sdist and wheel into `dist/`                             |
| `make build-clean`  | Remove `build/` and `dist/`                                    |
| `make publish`      | `uv publish` — upload built artifacts to PyPI                  |
| `make pre-commit-install` | Install the git `pre-commit` hook for this clone        |
| `make pre-commit-run`     | Run pre-commit on every tracked file                 |
| `make clean`        | `build-clean` + `docs-clean` + coverage/cache directories     |
| `make all`          | `lint` + `format-check` + `typecheck` + `security` + `test`    |

Initial bootstrap for a fresh clone:

```bash
make install
make pre-commit-install
make test
```

### Pre-commit Hooks

A `pre-commit` hook runs on every `git commit` and is configured in
`.pre-commit-config.yaml`. It uses **local** hooks that invoke the Makefile
targets, so tool versions stay pinned by `uv` and the hooks can't drift from
CI. The hook runs, in order, with `fail_fast: true`:

1. `make lint` — `ruff check` (syntax + style)
2. `make format-check` — `ruff format --check`
3. `make typecheck` — `mypy` (strict)
4. `make security` — `bandit -r src -ll` then `pip-audit`

Tests are intentionally **not** run in pre-commit; they run in CI instead
(`make test`) and locally before pushing. To bypass a hook for a one-off
(do not make this a habit), use `git commit --no-verify`.

Run the same checks against every tracked file without committing:

```bash
make pre-commit-run
```

Hooks must be installed per clone. New contributors run `make
pre-commit-install` after `make install`. `.git/hooks/pre-commit` is
generated by `pre-commit install` and is intentionally not tracked.

## Code Layout

```
.
├── AGENTS.md                    # this file
├── CHANGELOG.md                 # Keep a Changelog format, include in docs
├── LICENSE                      # MIT
├── Makefile                     # single entry point for all tooling
├── README.md                    # project landing page (also PyPI long desc)
├── pyproject.toml               # all packaging + tool configuration
├── uv.lock                      # committed for libraries (per uv guidance)
├── .github/
│   ├── dependabot.yml           # uv ecosystem weekly updates
│   └── workflows/ci.yml         # CI: lint, type, sec, test, build, publish
├── .readthedocs.yaml            # Read the Docs build configuration
├── docs/
│   ├── context/                 # NEW — project context for humans + agents (README, overview, glossary)
│   ├── plans/                   # historical record of plans / decisions (humans + agents)
│   └── sphinx/                  # Sphinx root (hosted user / developer docs; not for agents)
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
├── src/pylibreconcile/
│   ├── __init__.py              # public API entry point
│   └── py.typed                 # PEP 561 marker
└── tests/
    └── test_package.py
```

`docs/` may grow sibling folders (`docs/plans/`, `docs/notes/`, etc.) for
non-Sphinx content. Sphinx stays under `docs/sphinx/`.

## Tooling Notes

- **`uv sync --all-groups`** installs `dev`, `docs`, and runtime deps. Use it
  (via `make install`) instead of `uv add` for ad-hoc experimentation.
- **`uv add --dev <pkg>`** — use this when adding a new dev tool, not direct
  edits to `pyproject.toml`.
- **`uv add --group docs <pkg>`** — for Sphinx-related deps.
- **`uv add <pkg>`** — for runtime dependencies that go into `dependencies`.
- **`ruff`** owns linting AND formatting. Do not introduce `black`, `isort`,
  `flake8`, or `pylint`.
- **`mypy` is `strict`.** New modules must pass strict mode without
  per-module overrides. The only allowed override is `tests.*`.
- **`bandit`** security checks: keep `B101` (assert) skipped globally and
  skipped via per-file ignore in tests. Any new code that needs `B101`
  active should justify it in the PR.
- **`py.typed`** is present at `src/pylibreconcile/py.typed`. Do not delete.

## Documentation Rules

- Sphinx sources are **RST** by default. MyST Markdown is enabled for the
  changelog include only.
- Public API documentation is generated from docstrings via `sphinx.ext.autodoc`
  + `sphinx.ext.autosummary`. Keep docstrings on all public symbols.
- The changelog is rendered by including `CHANGELOG.md` with the
  `myst_parser.sphinx_` parser — keep `CHANGELOG.md` in MyST-flavoured
  Markdown.
- Read the Docs is built by `.readthedocs.yaml`; never reference paths like
  `docs/source/` — Sphinx root is `docs/sphinx/`.

## CI / Release Rules

- CI runs on every push and PR to `main`, plus every published release.
- Lint, type, security, test, build jobs always run.
- **Publishing to PyPI** is triggered *only* by a published GitHub Release
  (event `release`, type `published`). It is *not* triggered by push to
  `main`. To ship: cut a release in GitHub → CI builds + publishes.
- **Read the Docs** is built on every push (Read the Docs itself picks up
  commits via webhook). The optional `notify-readthedocs` workflow also
  fires on release to force a rebuild with the new version.
- Use trusted publishing (OIDC): configure PyPI project to trust this repo's
  `pypi` environment, no API tokens needed in CI long-term.
- `UV_PUBLISH_TOKEN` is only needed if trusted publishing is unavailable.

## Working Rules for Agents

0. **Check `.agents/rules/` for project-specific rules.** Additional rules
   live in `.agents/rules/*.md` and are loaded automatically.

1. **Never commit secrets.** No tokens, no email, no credentials. The author
   email in `pyproject.toml` is public — that's fine.
2. **Do not add code comments** unless the user explicitly asks for them.
3. **Prefer editing existing files** over creating new ones. Do not create
   new `.md` files unless the user asked.
4. **Mirror existing style.** Read neighbouring files first; match imports,
   naming, typing, and patterns.
5. **Run `make all` before considering work done.** All of lint, format,
   typecheck, security, and tests must pass.
6. **Update `CHANGELOG.md`** under the `[Unreleased]` section when changing
   behaviour. Use `Keep a Changelog` categories: `Added`, `Changed`,
   `Deprecated`, `Removed`, `Fixed`, `Security`.
7. **Version bumps** happen at release time. Do not manually edit
   `project.version` in `pyproject.toml` — the release process handles it
   (or the user will tell you to).
8. **CI failures**: when a job fails, run the matching `make` target locally
   to reproduce. Do not push speculative fixes without seeing the failure
   locally.
9. **Skill / subagent use**: delegate broad codebase exploration to the
   `explore` subagent. Delegate multi-step research tasks to the `general`
   subagent. Use the `context7-mcp` skill for library / framework API
   questions.
9a. **Concrete tasks → `code-worker` subagent (preferred)**: the model
    backing it (`my-opencode/poolside/laguna-s-2.1:free`) is free, so
    when a task has clearly-defined steps and edits — even ones the main
    agent could just do itself — delegate to it via the `task` tool with
    `subagent_type: "code-worker"` to save cost. It is defined in
    `.opencode/agents/code-worker.md` and operates as a strict executor.
    Its personal strength is code work (source edits, tests, refactors,
    bug fixes, broken-test fixes); clear and concise infrastructure or
    documentation edits are also good fits. Reserve the main agent for
    work that needs review, planning, prose drafting, full CI-style
    validation, architecture decisions, or design exploration — i.e. work
    where "figuring out what to do" is most of the job. The subagent may
    use `make test-fast` / `make typecheck` / `make lint` as feedback
    loops on its own work, but it does not run full validation pipelines,
    does not review, does not architect, and does not orchestrate. When
    delegating:
    - State the task and the exact files / functions expected to change.
    - Specify any hard constraints (style, API stability, public surface).
    - Point at any reference files to mirror.
    - Ask for the final output as the subagent's last message — no
      intermediate narration.
9b. **Git operations → `git-maintainer` subagent**: any git/GitHub
    action — staging, committing, pushing, worktree/branch/tag CRUD,
    PRs via `gh`, `.gitignore` / `.gitattributes` /
    `.pre-commit-config.yaml` edits, pre-commit hook diagnostics — goes
    through `git-maintainer` via `subagent_type: "git-maintainer"`.
    Defined at `.opencode/agents/git-maintainer.md` (model:
    `my-openrouter/google/gemma-4-31b-it:free`). It refuses to rewrite
    history (no `--amend`, `rebase`, `--hard` reset, or `--force` push)
    and edits only git-config files; source/test/doc fixes are delegated
    back to `code-worker`. Pre-commit hooks must be green before push —
    failures are reported back, not bypassed with `--no-verify`. Use this
    subagent for staging concerns, splitting src/tests/docs/tooling into
    separate commits per rule 11, and pushing branches / opening PRs.
10. **Do not delete `uv.lock`.** It is committed intentionally for libraries.
11. **See `.agents/rules/separate-commits.md`** for the rule on staging
    `src/`, `tests/`, and `docs/` as distinct commits.

## Quick Recipes

**Add a runtime dependency:**

```bash
uv add <package>
make install
make all
```

**Add a dev / testing tool:**

```bash
uv add --dev <package>
# then add config to the appropriate [tool.*] section in pyproject.toml
make install
make all
```

**Add a Sphinx-related dependency:**

```bash
uv add --group docs <package>
make install
make docs
```

**Cut a release:**

1. Move items from `[Unreleased]` in `CHANGELOG.md` to a new dated version
   section (`## [X.Y.Z] - YYYY-MM-DD`).
2. Update `project.version` in `pyproject.toml`.
3. Commit, push, and create a GitHub Release with tag `vX.Y.Z`.
4. CI publishes to PyPI automatically.

**Refresh lockfile:**

```bash
make lock
git add uv.lock
git commit -m "chore: refresh lockfile"
```
