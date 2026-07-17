# Changelog

## [0.2.0] — 2026-07-17

External review round; every finding verified against uvicorn 0.51 sources
before fixing.

- **SIGTERM no longer kills the teardown.** uvicorn's stock signal capture
  restores previous handlers after its shutdown and re-raises the captured
  signal — with default handlers the process died before ServiceRunner
  stopped the remaining services. The bridge now disables uvicorn's capture
  (`_QuietServer`) and owns the conversion: SIGINT/SIGTERM/SIGBREAK →
  graceful drain → full teardown → clean exit; a second signal forces a
  hard stop. Opt out with `handle_signals = False`. Covered by a subprocess
  test (SIGTERM on unix, CTRL_BREAK on Windows).
- **Failed FastAPI lifespan no longer blows through the rollback.** uvicorn
  0.50+ `sys.exit(3)`s inside the serve task; SystemExit from a task
  pierces the event loop past any `except`. The serve task now translates
  it into a `RuntimeError`, so `start()` fails normally and ServiceRunner
  rolls back. Regression test included.
- `stop()` honours a cancellation of its caller instead of swallowing it
  (the server task is cancelled alongside, then the cancellation re-raises).
- `Injected` resolver is now `async` — no more per-request threadpool hop
  for a container lookup — and takes Starlette's `HTTPConnection`, so it
  works in WebSocket dependencies too. For mounted sub-apps, attach the
  container to each sub-app (`request.app` is the innermost app).

## [0.1.0] — 2026-07-17

Initial release, extracted from a production WhatsApp gateway.

- `HttpService(ServiceInterface)` — uvicorn as a nexus lifecycle service:
  subclass, implement `create_app()`, set host/port. `start()` returns only
  after the socket is bound (startup failures raise immediately, so
  `ServiceRunner` rolls back cleanly); graceful idempotent `stop()`;
  `wait()` blocks until the server exits; `port = 0` + `bound_port` for
  ephemeral ports.
- `Injected(cls)` — a plain FastAPI `Depends` resolving from the nexus
  container; kills the per-service `get_x()` dependency boilerplate.
- `attach_container` / `get_container` — the underlying bridge, usable
  directly in TestClient setups and hand-written dependencies.
