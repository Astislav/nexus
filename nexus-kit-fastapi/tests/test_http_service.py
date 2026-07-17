import asyncio
import socket

import httpx
import pytest
from fastapi import FastAPI
from injector import singleton

from nexus_kit.impl import ContainerInjector, ServiceRunner
from nexus_kit.interfaces import ServiceInterface
from nexus_kit_fastapi import HttpService, Injected


@singleton
class Greeter:
    def greet(self) -> str:
        return "hello from the container"


@singleton
class PingService(HttpService):
    port = 0  # ephemeral — parallel-safe tests
    log_level = "warning"

    def create_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/ping")
        def ping(greeter: Greeter = Injected(Greeter)):
            return {"pong": greeter.greet()}

        return app


def test_full_lifecycle_serves_and_stops_cleanly():
    async def scenario():
        container = ContainerInjector({})
        service = container.get(PingService)

        await service.start()
        try:
            url = f"http://127.0.0.1:{service.bound_port}/ping"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
            assert response.status_code == 200
            assert response.json() == {"pong": "hello from the container"}
        finally:
            await service.stop()
            await service.stop()  # idempotent

    asyncio.run(scenario())


def test_runs_under_service_runner():
    async def scenario():
        container = ContainerInjector({})
        async with ServiceRunner(container, [PingService]):
            service = container.get(PingService)
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://127.0.0.1:{service.bound_port}/ping")
            assert response.status_code == 200
        # leaving the block stopped uvicorn; the port is released
        with pytest.raises(RuntimeError):
            _ = service.bound_port

    asyncio.run(scenario())


def test_failed_lifespan_raises_cleanly_and_rolls_back():
    """Regression: uvicorn 0.50+ sys.exit(3)s inside the serve task when the
    FastAPI lifespan fails — SystemExit from a task blows through the event
    loop past the rollback. The bridge translates it into a RuntimeError."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def broken_lifespan(app):
        raise RuntimeError("lifespan boom")
        yield  # pragma: no cover

    journal = []

    @singleton
    class First(ServiceInterface):
        def start(self):
            journal.append("+first")

        def stop(self):
            journal.append("-first")

    @singleton
    class BrokenApp(HttpService):
        port = 0
        log_level = "critical"
        handle_signals = False

        def create_app(self) -> FastAPI:
            return FastAPI(lifespan=broken_lifespan)

    async def scenario():
        container = ContainerInjector({})
        with pytest.raises(RuntimeError, match="uvicorn exited"):
            async with ServiceRunner(container, [First, BrokenApp]):
                pass

    asyncio.run(scenario())
    assert journal == ["+first", "-first"]  # rollback ran; no SystemExit blast


def test_failed_lifespan_releases_the_port_immediately():
    """Regression: the failed-startup path dropped the bound socket without
    closing it — the port lingered until GC and an in-process retry got
    EADDRINUSE."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def broken_lifespan(app):
        raise RuntimeError("lifespan boom")
        yield  # pragma: no cover

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()

    @singleton
    class BrokenOnPort(HttpService):
        port = free_port
        log_level = "critical"
        handle_signals = False

        def create_app(self) -> FastAPI:
            return FastAPI(lifespan=broken_lifespan)

    async def scenario():
        service = ContainerInjector({}).get(BrokenOnPort)
        with pytest.raises(RuntimeError):
            await service.start()
        rebind = socket.socket()  # must succeed at once — no lingering socket
        try:
            rebind.bind(("127.0.0.1", free_port))
        finally:
            rebind.close()

    asyncio.run(scenario())


def test_signal_handlers_are_saved_and_restored():
    """Regression: the bridge silently clobbered pre-existing signal handlers
    and left them gone after stop()."""
    import signal as signal_module

    sentinel_calls = []

    def sentinel(sig, frame):  # pragma: no cover — never actually fired
        sentinel_calls.append(sig)

    previous = signal_module.signal(signal_module.SIGINT, sentinel)
    try:

        @singleton
        class Quiet(HttpService):
            port = 0
            log_level = "critical"

            def create_app(self) -> FastAPI:
                return FastAPI()

        async def scenario():
            service = ContainerInjector({}).get(Quiet)
            await service.start()
            assert signal_module.getsignal(signal_module.SIGINT) is not sentinel  # bridge took over
            await service.stop()
            assert signal_module.getsignal(signal_module.SIGINT) is sentinel  # and gave it back

        asyncio.run(scenario())
    finally:
        signal_module.signal(signal_module.SIGINT, previous)


def test_start_raises_on_busy_port_instead_of_failing_silently():
    async def scenario():
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        busy_port = blocker.getsockname()[1]
        try:

            @singleton
            class Collider(HttpService):
                port = busy_port
                log_level = "critical"

                def create_app(self) -> FastAPI:
                    return FastAPI()

            container = ContainerInjector({})
            service = container.get(Collider)
            with pytest.raises(OSError):  # we bind the socket ourselves — a plain, catchable error
                await service.start()
        finally:
            blocker.close()

    asyncio.run(scenario())
