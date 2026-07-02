# Changelog

## [0.1.0] — 2025-07-02

Initial release.

### Added

- `ApplicationInterface` — abstract contract for application bootstrap
- `ContainerInterface` — abstract contract for dependency injection container
- `EnvironmentInterface` — abstract base for typed configuration (Pydantic BaseSettings + singleton)
- `Root` — path utility for development and PyInstaller-bundled environments
- `ContainerInjector` — `ContainerInterface` implementation using the `injector` library
- `nexus new <app-name>` CLI command to scaffold a minimal working application
