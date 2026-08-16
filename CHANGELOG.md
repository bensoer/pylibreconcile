# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `KnownStateHandler` protocol and its implementations:
  `LocalJSONKnownStateHandler`, `AzureStorageKnownStateHandler`, and
  `AWSS3KnownStateHandler`.
- `.gitmessage` Conventional Commits v1.0.0 commit message template at the
  repo root, plus a `make install-commit-template` Makefile target to
  wire it into git on this clone.

### Changed

- `AzureStorageKnownStateHandler` now authenticates with a
  `TokenCredential` (e.g. `DefaultAzureCredential`) and an `account_url`
  instead of a connection string.
- Git `pre-commit` hook that runs lint, format-check, typecheck, and security
  checks via the existing `make` targets. Install with `make pre-commit-install`.
- Initial project scaffolding.
