.PHONY: help install sync lock lint format format-check typecheck security test test-fast docs docs-strict docs-clean build build-clean publish pre-commit-install pre-commit-run install-commit-template clean all

help:
	@echo "pylibreconcile — make targets"
	@echo ""
	@echo "  install       Install all dependency groups via uv"
	@echo "  sync          Sync dependencies (uv sync --all-groups)"
	@echo "  lock          Refresh uv.lock (uv lock)"
	@echo "  lint          Run ruff linter"
	@echo "  format        Format code with ruff"
	@echo "  format-check  Check formatting without changes"
	@echo "  typecheck     Run mypy"
	@echo "  security      Run bandit and pip-audit"
	@echo "  test          Run pytest with coverage"
	@echo "  test-fast     Run pytest without coverage"
	@echo "  docs          Build Sphinx HTML docs"
	@echo "  docs-strict   Build Sphinx HTML, warnings as errors (CI/RTD)"
	@echo "  docs-clean    Remove built docs"
	@echo "  build         Build sdist and wheel"
	@echo "  build-clean   Remove build artifacts"
	@echo "  publish       Publish built artifacts to PyPI (uv publish)"
	@echo "  pre-commit-install  Install git pre-commit hooks"
	@echo "  pre-commit-run      Run pre-commit on all files"
	@echo "  install-commit-template  Configure .gitmessage as the git commit template (per clone)"
	@echo "  clean         Remove all build / cache artifacts"
	@echo "  all           Run lint, typecheck, security, test"
	@echo ""

install:
	uv sync --all-groups

sync:
	uv sync --all-groups

lock:
	uv lock

lint:
	uv run ruff check

format:
	uv run ruff format

format-check:
	uv run ruff format --check

typecheck:
	uv run mypy

security:
	uv run bandit -r src -ll
	uv run pip-audit

test:
	uv run pytest

test-fast:
	uv run pytest --no-cov

docs:
	uv run sphinx-build -b html docs/sphinx/source docs/sphinx/build/html

docs-strict:
	uv run sphinx-build -b html -W --keep-going docs/sphinx/source docs/sphinx/build/html

docs-clean:
	rm -rf docs/sphinx/build

build:
	uv run python -m build

build-clean:
	rm -rf build dist

publish:
ifdef UV_PUBLISH_URL
	uv publish --publish-url $(UV_PUBLISH_URL)
else
	uv publish
endif

pre-commit-install:
	uv run pre-commit install

pre-commit-run:
	uv run pre-commit run --all-files

install-commit-template:
	git config commit.template .gitmessage

clean: build-clean docs-clean
	rm -rf .coverage .coverage.* coverage.xml htmlcov
	rm -rf .pytest_cache .mypy_cache .ruff_cache .bandit_cache
	find . -type d -name '__pycache__' -exec rm -rf {} +

all: lint format-check typecheck security test
