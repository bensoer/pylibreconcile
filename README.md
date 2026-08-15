# pylibreconcile

Reconciliation utilities for processing data against reference sources.

## Installation

```bash
pip install pylibreconcile
```

## Usage

```python
import pylibreconcile

print(pylibreconcile.hello())
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.
All day-to-day commands go through the top-level `Makefile` — do not invoke
`uv`, `ruff`, `mypy`, `pytest`, `bandit`, or `sphinx-build` directly.

```bash
make help         # list all targets
make install      # install all dependency groups
make test         # run tests with coverage
make lint         # ruff check
make format       # ruff format (writes changes)
make format-check # ruff format --check (CI mode)
make typecheck    # mypy
make security     # bandit + pip-audit
make docs         # build Sphinx HTML
make build        # build sdist and wheel
make clean        # remove build / cache artifacts
make all          # lint + format-check + typecheck + security + test
```

Run `make all` before opening a PR — it is the same gate the CI pipeline runs.

## License

MIT
