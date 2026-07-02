# Nexus — AI Agent Guide

Context for AI assistants working in projects built with nexus.

## What nexus is

Nexus is a minimal Python application framework. It provides:

- Interfaces (abstract contracts) for bootstrapping an application
- `ContainerInjector` — a concrete DI container implementation
- `Root` — a path utility that works in dev and PyInstaller-bundled environments

Nexus does NOT contain domain logic, UI code, or data access. It is infrastructure only.

## Package layout

```
nexus/
├── interfaces/          # abstract contracts — always import from here first
│   ├── application.py   # ApplicationInterface
│   ├── container.py     # ContainerInterface
│   └── environment.py   # EnvironmentInterface
├── impl/                # concrete implementations — import explicitly
│   └── container_injector.py
└── root.py              # Root utility
```

Import conventions:

```python
from nexus.interfaces import ApplicationInterface, ContainerInterface, EnvironmentInterface
from nexus.impl import ContainerInjector   # explicit — this is a concrete choice
from nexus import Root
```

## Bootstrap pattern

Every nexus-based app follows this sequence in `main.py`:

```python
env = Environment(Root.external(".env"))      # 1. load config
container = ContainerInjector(DI_CONFIG)      # 2. wire dependencies
Application(env, container).run()             # 3. start app
```

`Environment` extends `EnvironmentInterface`, `Application` extends `ApplicationInterface`.
`DI_CONFIG` lives in `app/config/di.py` — it is the composition root.

## How to extend ApplicationInterface

```python
from nexus.interfaces import ApplicationInterface, ContainerInterface, EnvironmentInterface

class Application(ApplicationInterface):
    def __init__(self, environment: EnvironmentInterface, container: ContainerInterface) -> None:
        self._env = environment
        self._container = container
        # resolve top-level services here:
        # self._service = container.get(SomeServiceInterface)

    def run(self) -> None:
        ...  # start event loop, server, CLI, etc.
```

## How to extend EnvironmentInterface

```python
from pathlib import Path
from injector import singleton
from nexus.interfaces import EnvironmentInterface

@singleton
class Environment(EnvironmentInterface):
    DATABASE_URL: str
    DEBUG: bool = False
    MAX_WORKERS: int = 4

    def __init__(self, env_path: Path) -> None:
        super().__init__(_env_file=env_path)
```

Pydantic BaseSettings rules apply: values come from environment variables and the `.env` file.
Pass the `.env` path via `Root.external(".env")`.

## How to register services in DI

Composition root lives in `app/config/di.py`:

```python
from app.services.greeter import Greeter
from app.services.greeter_interface import GreeterInterface

DI_CONFIG = {
    GreeterInterface: Greeter,
    # Interface: ConcreteImplementation
}
```

Mark long-lived services with `@singleton`, use `@inject` for constructor injection:

```python
from injector import inject, singleton
from app.services.dep_interface import DepInterface

@singleton
class Greeter(GreeterInterface):
    @inject
    def __init__(self, dep: DepInterface) -> None:
        self._dep = dep
```

## Key conventions

- Abstract contracts have the `Interface` suffix: `GreeterInterface`, `UserRepositoryInterface`
- Implementations have no special suffix: `Greeter`, `UserRepository`
- One class per file; file named after the class in snake_case
- `@singleton` for long-lived managers and services
- Dynamic objects (created at runtime) use Factories: `WidgetFactoryInterface` → `WidgetFactory`
- Do not import concrete implementations outside of `di.py` (except in tests)

## What NOT to do

- Do not put business logic in `Application.__init__` or `main.py`
- Do not make `ContainerInterface` globally accessible — pass it only to `Application`
- Do not register primitive types (str, int, bool) in DI unless they carry policy semantics
- Do not add `@inject` to `Application.__init__` — it is constructed manually in `main.py`
