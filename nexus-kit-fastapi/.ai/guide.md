<!-- when: exposing an HTTP API, running FastAPI/uvicorn as a nexus service, or injecting container objects into route handlers -->
# nexus-kit-fastapi — AI Agent Guide

Context for AI assistants working in projects that use `nexus-kit-fastapi`
(PyPI dist `nexus-kit-fastapi`, import `nexus_kit_fastapi`). Read the core
guide first: nexus-kit's guide. (In a consumer app this file is written into
`.nexus-kit/guides/nexus-kit-fastapi.md` by `uv run nexus-kit guides` and
indexed by `.nexus-kit/map.md`; do not edit the generated copy by hand.)

## What it is

A bridge between FastAPI and the nexus-kit kernel. Two things, nothing else:

- `HttpService(ServiceInterface)` — uvicorn as a nexus lifecycle service.
- `Injected(cls)` — a plain FastAPI `Depends` resolving `cls` from the nexus
  container (plus `attach_container`/`get_container` underneath).

FastAPI remains fully in charge of HTTP: routers, middleware, auth, OpenAPI
are written in plain FastAPI idioms. Do not look here for routing helpers.

## HttpService

Subclass it; implement `create_app()`; feed host/port from Environment:

```python
@singleton
class ApiService(HttpService):
    @inject
    def __init__(self, env: Environment, container: ContainerInterface) -> None:
        super().__init__(container)
        self.host, self.port = env.HOST, env.PORT

    def create_app(self) -> FastAPI:
        app = FastAPI(title="my api")
        app.include_router(my_router)
        return app
```

Contract:
- `start()` binds the socket itself, synchronously — a busy port raises a
  plain `OSError` in `start()`, so ServiceRunner rolls back cleanly; a
  failed FastAPI lifespan (uvicorn's in-task `sys.exit`) is translated into
  a normal `RuntimeError` for the same reason. Cancelling a still-starting
  `start()` tears everything down (serve task, socket, signal handlers);
  `start()` on an already-started service raises `RuntimeError`.
- `stop()` is a graceful uvicorn shutdown, idempotent; a cancellation of
  the caller is honoured, not swallowed — and the port is released either
  way (a ServiceRunner `stop_grace` timeout takes exactly this path).
- `wait()` blocks until the server exits — the natural Application body:
  `async with ServiceRunner(...): await container.get(ApiService).wait()`.
- Signals are handled BY THE BRIDGE (default `handle_signals = True`):
  SIGINT/SIGTERM/SIGBREAK → graceful drain → wait() returns → the runner
  stops everything. uvicorn's own capture is disabled because it re-raises
  the signal after shutdown, killing the process mid-teardown. Opt out with
  `handle_signals = False` only if the application owns signals itself.
- `port = 0` binds an ephemeral port; read it via `service.bound_port`.
- Override `uvicorn_config(app)` for TLS/proxy-headers or to wrap the app
  in ASGI middleware (e.g. `socketio.ASGIApp`) — plain uvicorn API.

## Injected — routes reach the container

```python
@router.post("/send")
async def send(text: str, sender: Sender = Injected(Sender)) -> None:
    await sender.enqueue(text)
```

`Injected(cls)` is an ordinary FastAPI dependency — it composes with auth
dependencies, `Annotated`, sub-dependencies. Do NOT write per-service
`get_x(request)` dependency functions; that boilerplate is exactly what
`Injected` replaces.

Tests without a server: `attach_container(app, container)` + FastAPI
`TestClient`; override by binding fakes — `container.set(Sender, fake)`.

## What NOT to do

- Do not manage service lifecycle in a FastAPI lifespan — the Application's
  ServiceRunner owns start/stop order; the HTTP edge is one service among
  many (typically last in `SERVICES`: last up, first down).
- Do not construct domain objects inside route handlers — resolve them via
  `Injected` from the one container.
- Do not install your own signal handlers while `handle_signals = True`
  (the default) — the bridge already converts them into a graceful drain.
- Do not pass the container around explicitly in routes — `Injected` exists
  so handlers never see `ContainerInterface`.
