import sys
from importlib.metadata import version
from pathlib import Path


_TEMPLATES: dict[str, str] = {
    "main.py": """\
import faulthandler

from app.application import Application
from app.config.di import DI_CONFIG
from app.config.environment import Environment
from nexus import Root
from nexus.impl import ContainerInjector

if __name__ == "__main__":
    faulthandler.enable(all_threads=True)

    env = Environment(Root.external(".env"))
    container = ContainerInjector(DI_CONFIG)
    container.set(Environment, env)
    Application(env, container).run()
""",
    "pyproject.toml": """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{APP_NAME}}"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "nexus @ git+https://github.com/Astislav/nexus@{{NEXUS_REF}}",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]
""",
    ".env": """\
APP_NAME={{APP_NAME}}
DEBUG=false
""",
    "app/__init__.py": "",
    "app/application.py": """\
from nexus.interfaces import ApplicationInterface, ContainerInterface

from app.config.environment import Environment
from app.services.greeter_interface import GreeterInterface


class Application(ApplicationInterface):
    def __init__(self, environment: Environment, container: ContainerInterface) -> None:
        self._env = environment
        self._greeter = container.get(GreeterInterface)

    def run(self) -> None:
        print(f"[{self._env.APP_NAME}] debug={self._env.DEBUG}")
        print(self._greeter.greet("world"))
""",
    "app/config/__init__.py": "",
    "app/config/di.py": """\
# Register your services here: {Interface: Implementation}
from app.services.greeter import Greeter
from app.services.greeter_interface import GreeterInterface

DI_CONFIG = {
    GreeterInterface: Greeter,
}
""",
    "app/config/environment.py": """\
from pathlib import Path

from injector import singleton

from nexus.interfaces import EnvironmentInterface


@singleton
class Environment(EnvironmentInterface):
    # Add your config fields here — they are read from .env automatically
    APP_NAME: str = "{{APP_NAME}}"
    DEBUG: bool = False

    def __init__(self, env_path: Path) -> None:
        super().__init__(_env_file=env_path)
""",
    "app/services/__init__.py": "",
    "app/services/greeter_interface.py": """\
from abc import ABC, abstractmethod


class GreeterInterface(ABC):
    @abstractmethod
    def greet(self, name: str) -> str: ...
""",
    "app/services/greeter.py": """\
from injector import singleton

from app.services.greeter_interface import GreeterInterface


@singleton
class Greeter(GreeterInterface):
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
""",
    "CLAUDE.md": """\
# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

This app is built on the **nexus** framework. Its API, the bootstrap pattern and the
gotchas are in `.ai/nexus.md` — read it before touching DI, config or the composition
root (`app/config/di.py`). Keep this file thin: put engineering discipline in `.ai/`
and only repo-specific facts here.
""",
    ".ai/nexus.md": """\
# Nexus — quick reference (how to build an app on this framework)

Compact cheat-sheet for the **nexus** framework (github.com/Astislav/nexus), pinned to
**{{NEXUS_REF}}**. For depth: the framework's own `.ai/guide.md`, or the installed source at
`.venv/Lib/site-packages/nexus/`.

## What it is

A tiny application bootstrap: a **DI container** (wraps `injector`) + a **config base**
(wraps `pydantic-settings`) + **logging** + **`Root`** (paths) + the `nexus new` CLI.
No domain, HTTP or DB.

## Public API

| Symbol | Import | Role |
|---|---|---|
| `ApplicationInterface` | `nexus.interfaces` | run contract: `__init__(env, container)` + `run()` |
| `ContainerInterface` | `nexus.interfaces` | DI contract: `get(cls)`, `set(cls, value)` |
| `EnvironmentInterface` | `nexus.interfaces` | typed config base (pydantic BaseSettings + `@singleton`) |
| `Root` | `nexus` | paths: `Root.internal(*p)` (bundled assets) / `Root.external(*p)` (files next to the exe — or next to `main.py` in dev: `.env`, db) |
| `ContainerInjector` | `nexus.impl` | concrete container; constructor takes `DI_CONFIG: dict[Type, Impl]` |
| `NamedLogger` / `StdoutHandler` / `LogFormatter` | `nexus.logging` | DI-injectable logging |

**Gotcha:** `@singleton`, `@inject`, `Injector` come from the `injector` package, NOT
from nexus (`from injector import inject, singleton`). Nexus never re-exports them.

**Dependencies:** `injector` and `pydantic-settings` are core dependencies of nexus —
no extras, everything works out of the box.

## Bootstrap (`main.py`)

```python
env = Environment(Root.external(".env"))   # 1. config
container = ContainerInjector(DI_CONFIG)   # 2. wiring
container.set(Environment, env)            # 3. env is NOT auto-bound — bind it by hand
Application(env, container).run()          # 4. start
```

- `DI_CONFIG` (composition root) is a `dict{Interface: Impl}`; register only swappable
  seams — `@singleton @inject` services are built by the container from their constructors.
- **Do not bind a class to itself.** Interfaces carry the `Interface` suffix; implementations don't.
- Long-lived services are `@singleton`, dependencies come via an `@inject` constructor.
- Logging: subclass `NamedLogger` (class attr `name`), inject by type; change the format
  by rebinding `LogFormatter` in `DI_CONFIG`.

## What nexus does NOT provide (you hand-roll these)

Lifecycle orchestration (ordered start/stop, shutdown, signals — in your `Application.run()`);
a background-service/worker base; a repository/DB layer; a test harness; HTTP/routing/retries.
""",
}


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] != "new":
        print("Usage: nexus new <app-name>")
        sys.exit(1)

    app_name = sys.argv[2]
    root = Path(app_name)

    if root.exists():
        print(f"Error: '{app_name}' already exists")
        sys.exit(1)

    root.mkdir()

    nexus_ref = f"v{version('nexus')}"
    for rel_path, content in _TEMPLATES.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        content = content.replace("{{APP_NAME}}", app_name).replace("{{NEXUS_REF}}", nexus_ref)
        path.write_text(content, encoding="utf-8")

    print(f"Created {app_name}/")
    print(f"")
    print(f"  cd {app_name}")
    print(f"")
    print(f"  # install dependencies:")
    print(f"  uv sync                  # uv")
    print(f"  pip install -e .         # pip")
    print(f"")
    print(f"  python main.py")
