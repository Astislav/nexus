# Changelog

## [0.1.1]

### Added

- `nexus.logging` — DI-injectable logging base (`NamedLogger`, `StdoutHandler`, `LogFormatter`). Present since the initial release but previously undocumented in this changelog.
- `nexus new <app-name>` now scaffolds an AI-ready project: a `CLAUDE.md` pointing to `.ai/`, and `.ai/nexus.md` (a compact, self-contained Nexus API reference) so any AI assistant picks up how to build on nexus without reading the framework source.

### Changed

- Refreshed `.ai/guide.md` (AI Agent Guide): package layout now lists `logging/` and `cli.py`; documents the `injector`-not-nexus import gotcha, the `nexus[pydantic]` extra requirement, and what nexus deliberately does NOT provide.

## [0.1.0] — 2025-07-02

Initial release.

### Added

- `ApplicationInterface` — abstract contract for application bootstrap
- `ContainerInterface` — abstract contract for dependency injection container
- `EnvironmentInterface` — abstract base for typed configuration (Pydantic BaseSettings + singleton)
- `Root` — path utility for development and PyInstaller-bundled environments
- `ContainerInjector` — `ContainerInterface` implementation using the `injector` library
- `nexus new <app-name>` CLI command to scaffold a minimal working application
