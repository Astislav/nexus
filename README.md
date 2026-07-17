# nexus-kit

[![PyPI](https://img.shields.io/pypi/v/nexus-kit)](https://pypi.org/project/nexus-kit/)
[![CI](https://github.com/Astislav/nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/Astislav/nexus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A minimal application kernel for long-lived Python apps: one entry point,
typed config, constructor DI, logger channels, service lifecycle — and a
packaging story that survives PyInstaller.

## Why

If you build long-lived Python apps **outside a web framework's cradle** —
a Qt tool driving hardware, a pygame game, a Windows daemon, an API server
where uvicorn is just one service among many — you end up hand-rolling the
same bootstrap in every repo: an entry point, `.env` parsing, wiring
services together, logging setup, ordered start/stop, and the
`sys._MEIPASS` dance for frozen builds.

nexus-kit is that bootstrap extracted once and turned into a convention.
Every app gets the same shape: `main.py` is four lines, config is a typed
class, services declare dependencies in constructors, long-lived services
start in order and stop in reverse — guaranteed. Your fifth app looks like
your first, and anyone (human or AI assistant) who has seen one has seen
them all.

## From zero to a shipped exe

```bash
uv tool install nexus-kit      # or: uv add nexus-kit in an existing project

nexus-kit new my-app           # scaffold: typed config, DI, lifecycle demo
cd my-app && uv sync
python main.py                 # a worker ticks, stops cleanly — the whole shape

nexus-kit freeze               # once: generate app.spec (PyInstaller)
nexus-kit build                # every release: clean build → dist/my-app.exe
```

`build` is the same command on Windows, Linux and macOS — no `.bat`/`.sh`
to keep in sync. Bundled assets live inside the exe (`Root.internal`),
operator files land next to it (`Root.external`); your real `.env` never
ships unless you say `--env`. The full path — scaffold → freeze → build →
run the exe — is exercised by CI on every push.

**Full documentation → [nexus-kit/README.md](nexus-kit/README.md)**
(environment, DI, lifecycle guarantees, logging, paths, freezing).

## Packages

This is a uv-workspace monorepo; each directory is an independently
versioned PyPI distribution.

| Package | PyPI | What it is |
|---------|------|------------|
| [`nexus-kit`](nexus-kit/) | [![PyPI](https://img.shields.io/pypi/v/nexus-kit)](https://pypi.org/project/nexus-kit/) | The kernel: entry point, typed config, DI, logger channels, service lifecycle, PyInstaller-safe paths, `new`/`freeze`/`build` CLI |
| [`nexus-kit-fastapi`](nexus-kit-fastapi/) | [![PyPI](https://img.shields.io/pypi/v/nexus-kit-fastapi)](https://pypi.org/project/nexus-kit-fastapi/) | FastAPI + uvicorn as a lifecycle service, `Injected(cls)` Depends bridge into the container |

Satellites are extracted from real apps as they migrate — next up:
`nexus-kit-postgres` (asyncpg pool as a lifecycle service).

Every package carries a machine-oriented `.ai/guide.md` (API contract,
conventions, anti-patterns) — point AI assistants at it instead of the
source: [nexus-kit](nexus-kit/.ai/guide.md) ·
[nexus-kit-fastapi](nexus-kit-fastapi/.ai/guide.md).

## Development

```bash
uv sync --all-packages   # one shared venv for every package in the workspace
uv run pytest            # run every package's tests
uv run ruff check .
```

Releases are tag-driven: `v1.2.3` publishes `nexus-kit`;
`<name>-v1.2.3` publishes `nexus-kit-<name>`.

**New package checklist** — a directory beside the others, named after its
PyPI dist (dir = dist name = tag prefix), containing: `pyproject.toml`,
`src/<import_name>/`, `tests/`, `README.md` (with a *For AI assistants*
section), `CHANGELOG.md`, `LICENSE`, and **`.ai/guide.md`**. Plus one
pending publisher on PyPI and a row in the table above.

**AI-guide discipline**: `.ai/guide.md` changes in the same commit as the
public API it describes — a stale machine guide is worse than none, an
agent will confidently build against a dead contract. Docs describe donor
apps by class (a gateway, an analytics service), never by product name.

## License

MIT © Astislav Bozhevolnov
