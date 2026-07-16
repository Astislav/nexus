# nexus

A minimal application kernel for long-lived Python apps: one entry point,
typed config, constructor DI, logger channels, service lifecycle — and paths
that survive PyInstaller.

## Why

If you build long-lived Python apps **outside a web framework's cradle** — a
Qt tool driving hardware, a pygame game, a Windows daemon, an API server
where uvicorn is just one service among many — you end up hand-rolling the
same bootstrap in every repo: an entry point, `.env` parsing, wiring services
together, logging setup, ordered start/stop, and the `sys._MEIPASS` dance for
frozen builds.

nexus is that bootstrap extracted once and turned into a convention. Every
app gets the same shape: `main.py` is four lines, config is a typed class,
services declare their dependencies in constructors, long-lived services
start in order and stop in reverse — guaranteed. Your fifth app looks like
your first, and anyone (human or AI assistant) who has seen one has seen
them all.

## Who it's for

- You ship Python as **PyInstaller executables** and are tired of path bugs
  that only appear after freezing.
- You maintain **several apps** — web and not — and want them all shaped the
  same instead of each inventing its own bootstrap.
- You want **constructor injection without magic**: one explicit
  `{Interface: Implementation}` dict, no string keys, no globals, no
  auto-scanning.
- Your app has **services that must start in order and stop cleanly** —
  DB pools, pollers, device monitors, an embedded HTTP server.

## Who it's NOT for

- **Short scripts.** A module with functions is already dependency
  injection. This would be ceremony.
- **Apps living happily inside FastAPI/Django conventions.** Their lifespan
  and DI are enough; nexus solves the world outside that cradle.
- **Teams that want a mainstream stack.** This is an opinionated personal
  kernel: conventions over ecosystem, no Stack Overflow answers.

## What it is, honestly

Opinionated glue — not invention. Config is stock
[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
DI is stock [injector](https://injector.readthedocs.io/); nexus adds the
parts nobody packages: the `Root` path resolver for frozen builds, typed
logger channels, the `ServiceRunner` lifecycle, a scaffolder, and the
convention that ties them together. Extracted from real production apps
(a Qt device farm, a WhatsApp gateway, analytics services), not designed in
a vacuum.

## Install

```bash
# uv
uv add "nexus @ git+https://github.com/Astislav/nexus@v0.3.1"

# pip
pip install "nexus @ git+https://github.com/Astislav/nexus@v0.3.1"
```

Requires Python 3.12+. Ships with [injector](https://injector.readthedocs.io/) and
[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) —
no extras, everything works out of the box.

## Bootstrap a new app

```bash
nexus new my-app
cd my-app

# install dependencies:
uv sync          # uv
pip install -e . # pip

python main.py
# [heartbeat] started
# [my-app] debug=False
# Hello, world!
# [heartbeat] stopped
```

## What you get

```
my-app/
├── main.py                          # entry point
├── pyproject.toml
├── .env
└── app/
    ├── application.py               # extend ApplicationInterface; SERVICES + ServiceRunner
    ├── config/
    │   ├── di.py                    # DI_CONFIG = {Interface: Implementation}
    │   └── environment.py           # extend EnvironmentInterface
    └── services/
        ├── heartbeat.py             # example ServiceInterface (start/stop lifecycle)
        ├── greeter_interface.py     # example interface
        └── greeter.py               # example implementation
```

## How it fits together

```python
# main.py — the whole bootstrap
env       = Environment(Root.external(".env"))  # 1. load typed config
container = ContainerInjector(DI_CONFIG)         # 2. wire up services
container.set(Environment, env)                  # 3. make config injectable
Application(env, container).run()                # 4. start the app
```

| File | Role |
|------|------|
| `app/config/environment.py` | Declare config fields — read from `.env` automatically |
| `app/config/di.py` | Register services — `{Interface: Implementation}` |
| `app/application.py` | Entry point — resolve services, own the `run()` lifecycle |

## Environment

`EnvironmentInterface` is a [Pydantic BaseSettings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) subclass.
Add typed fields — they are read from `.env` automatically:

```python
# app/config/environment.py
from nexus.interfaces import EnvironmentInterface

class Environment(EnvironmentInterface):
    APP_NAME: str = "my-app"
    DEBUG: bool = False
    DB_URL: str = "sqlite:///data.db"
```

`.env` is passed at startup via `Root.external(".env")` (see below):

```python
env = Environment(Root.external(".env"))
```

Fields can be overridden at runtime with environment variables — Pydantic picks them up automatically.

`Environment` is also bound into the container at startup, so services can inject it directly:

```python
# main.py (generated by `nexus new`)
env = Environment(Root.external(".env"))
container = ContainerInjector(DI_CONFIG)
container.set(Environment, env)   # ← makes env injectable
Application(env, container).run()
```

This means any service can receive config via `@inject` without going through `Application`:

```python
from injector import inject, singleton
from app.config.environment import Environment

@singleton
class DatabaseService:
    @inject
    def __init__(self, env: Environment) -> None:
        self._url = env.DB_URL
```

## Paths

`Root` resolves paths correctly in both development and PyInstaller-bundled executables.

```python
from nexus import Root

# next to the .exe (or next to main.py in dev) — user data, configs, output
config = Root.external(".env")
db     = Root.external("data", "app.db")

# inside the bundle (or next to main.py in dev) — shipped assets, templates
html   = Root.internal("templates", "report.html")
```

| Method | Dev (plain Python) | Bundled (PyInstaller) |
|--------|--------------------|-----------------------|
| `Root.external(...)` | `dir(main.py) / path` | `dir(exe) / path` |
| `Root.internal(...)` | `dir(main.py) / path` | `_MEIPASS / path` |

In dev the anchor is the entry script's directory (not the current working
directory), so launching `python d:/apps/game/main.py` from anywhere — an IDE,
a task scheduler, a shortcut — resolves the same paths as running it in place.

Use `external` for anything the user owns (configs, databases, output files).
Use `internal` for assets you ship inside the bundle (templates, images, default configs).

## Logging

`NamedLogger` is a base for typed, DI-injectable logger channels — subclass
it, set `name`, and inject the subclass by type. No string-keyed
`logging.getLogger(...)` calls scattered through the codebase:

```python
# app/loggers.py
from injector import singleton
from nexus.logging import NamedLogger

@singleton
class SessionLogger(NamedLogger):
    name = "app.session"

@singleton
class SenderLogger(NamedLogger):
    name = "app.sender"
```

```python
# app/core/session_manager.py
from injector import inject, singleton
from app.loggers import SessionLogger

@singleton
class SessionManager:
    @inject
    def __init__(self, log: SessionLogger) -> None:
        self._log = log

    def start(self) -> None:
        self._log.info("Session manager started")
```

Each subclass gets its own `StdoutHandler` (console, one shared instance)
wired up automatically — no duplicate-handler bugs, no manual `addHandler`.

**Custom format** — *where* logs go (`StdoutHandler`) and *how they look*
(`LogFormatter`) are separate, like in stdlib `logging`. Subclass
`LogFormatter` and rebind it — no need to touch the handler:

```python
# app/loggers.py
from nexus.logging import LogFormatter

class JsonFormatter(LogFormatter):
    format_string = '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
```

```python
# app/config/di.py
DI_CONFIG = {
    LogFormatter: JsonFormatter,
    ...
}
```

**Extra handlers** (e.g. forwarding logs to a UI widget) — override `__init__`
and add the handler after calling `super().__init__(handler)`:

```python
@singleton
class SessionLogger(NamedLogger):
    name = "app.session"

    @inject
    def __init__(self, handler: StdoutHandler, ui_handler: LogViewHandler) -> None:
        super().__init__(handler)
        self.addHandler(ui_handler)
```

## Services & lifecycle

`ServiceInterface` + `ServiceRunner` manage long-lived services: started in
declaration order, stopped in reverse — guaranteed, even when startup or the
app body crashes.

```python
# a service — sync or async, the runner handles both
from injector import singleton
from nexus.interfaces import ServiceInterface

@singleton
class Database(ServiceInterface):
    async def start(self) -> None: ...   # open the pool
    async def stop(self) -> None: ...    # close the pool (must be idempotent)
```

```python
# app/application.py — async app (uvicorn, workers)
from nexus.impl import ServiceRunner

class Application(ApplicationInterface):
    SERVICES = [Database, WebhookDispatcher, HttpApiService]  # startup order

    def run(self) -> None:
        asyncio.run(self._serve())

    async def _serve(self) -> None:
        async with ServiceRunner(self._container, self.SERVICES):
            await self._container.get(HttpApiService).wait()
        # leaving the block stops everything in reverse order
```

Sync apps (pygame, Qt with worker threads) use the plain context manager:

```python
    def run(self) -> None:
        with ServiceRunner(self._container, self.SERVICES):
            self._main_loop()
```

Guarantees:

- start in order, stop in reverse — on normal exit, exception, Ctrl+C;
- crash-safe startup: if the N-th `start()` fails, the already started N-1
  are stopped in reverse and the error re-raises;
- one failing `stop()` doesn't block the rest — it is logged and teardown
  continues;
- in the async context each `stop()` is bounded by `stop_grace` seconds
  (default 10), then cancelled.

The runner installs **no signal handlers** — who triggers the exit is your
app's business (uvicorn's own handlers, Qt's `aboutToQuit`, or your own).

## Add a service

**1. Define an interface:**

```python
# app/services/greeter_interface.py
from abc import ABC, abstractmethod

class GreeterInterface(ABC):
    @abstractmethod
    def greet(self, name: str) -> str: ...
```

**2. Implement it:**

```python
# app/services/greeter.py
from injector import inject, singleton
from app.services.greeter_interface import GreeterInterface

@singleton
class Greeter(GreeterInterface):
    @inject
    def __init__(self) -> None: ...

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
```

**3. Register in DI:**

```python
# app/config/di.py
from app.services.greeter import Greeter
from app.services.greeter_interface import GreeterInterface

DI_CONFIG = {
    GreeterInterface: Greeter,
}
```

**4. Use in Application:**

```python
# app/application.py
from nexus.interfaces import ApplicationInterface, ContainerInterface, EnvironmentInterface
from app.services.greeter_interface import GreeterInterface

class Application(ApplicationInterface):
    def __init__(self, environment: EnvironmentInterface, container: ContainerInterface) -> None:
        self._greeter = container.get(GreeterInterface)

    def run(self) -> None:
        print(self._greeter.greet("world"))
```

## What nexus provides

| Symbol | Import | Description |
|--------|--------|-------------|
| `ApplicationInterface` | `nexus.interfaces` | Bootstrap contract: `__init__(env, container)` + `run()` |
| `ContainerInterface` | `nexus.interfaces` | DI contract: `get(cls)` + `set(cls, value)` |
| `EnvironmentInterface` | `nexus.interfaces` | Typed config base (Pydantic BaseSettings) |
| `ServiceInterface` | `nexus.interfaces` | Long-lived service contract: `start()` + `stop()`, sync or async |
| `Root` | `nexus` | Path util for dev and PyInstaller-bundled environments |
| `ContainerInjector` | `nexus.impl` | `ContainerInterface` impl via [injector](https://injector.readthedocs.io/) |
| `ServiceRunner` | `nexus.impl` | Ordered start / guaranteed reverse-order stop (`with` / `async with`) |
| `NamedLogger` | `nexus.logging` | Base for typed, DI-injectable logger channels |
| `StdoutHandler` | `nexus.logging` | Shared console handler — *where* logs go |
| `LogFormatter` | `nexus.logging` | Default log line format — *how* logs look; subclass to customize |

## What nexus does NOT provide

Domain logic, UI, data access — those belong in your app.

## License

MIT © Astislav Bozhevolnov
