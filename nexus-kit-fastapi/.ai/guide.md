# nexus-kit-fastapi — AI Agent Guide

Context for AI assistants working in projects that use `nexus-kit-fastapi`
(PyPI dist `nexus-kit-fastapi`, import `nexus_kit_fastapi`). Read the core
guide first: nexus-kit's `.ai/guide.md`.

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
  plain `OSError` in `start()`, so ServiceRunner rolls back cleanly.
- `stop()` is a graceful uvicorn shutdown, idempotent.
- `wait()` blocks until the server exits — the natural Application body:
  `async with ServiceRunner(...): await container.get(ApiService).wait()`.
- `port = 0` binds an ephemeral port; read it via `service.bound_port`.
- Override `uvicorn_config(app)` for TLS/proxy-headers — plain uvicorn API.

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
- Do not install signal handlers — uvicorn's own handlers end `wait()`.
- Do not pass the container around explicitly in routes — `Injected` exists
  so handlers never see `ContainerInterface`.
