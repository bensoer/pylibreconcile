# Separate code, docs, and tests into distinct commits

Stage and commit `src/`, `tests/`, and `docs/` as separate commits — never
mix them in a single commit.

```bash
git add src/
git commit -m "feat: ..."

git add tests/
git commit -m "test: ..."

git add docs/
git commit -m "docs: ..."
```

Tooling and config changes (`pyproject.toml`, `uv.lock`, `Makefile`,
`.github/`, `.pre-commit-config.yaml`, `AGENTS.md`, `CHANGELOG.md`) are
their own commits and may not be bundled with code/docs/test commits.

Use Conventional Commits prefixes: `feat:`, `fix:`, `refactor:`, `test:`,
`docs:`, `chore:`, `build:`, `ci:`.