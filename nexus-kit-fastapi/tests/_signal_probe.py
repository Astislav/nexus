"""Subprocess probe for the signal test.

Starts a Marker service + HttpService under ServiceRunner, prints READY,
then blocks on wait(). The parent test sends SIGTERM (unix) or CTRL_BREAK
(Windows). A correct bridge converts it into a graceful drain: wait()
returns, the runner stops every service (MARKER-STOPPED), main() reaches
CLEAN-EXIT, exit code 0. With uvicorn's stock signal handling the re-raised
signal would kill the process before MARKER-STOPPED.
"""
import asyncio

from fastapi import FastAPI
from injector import singleton

from nexus_kit.impl import ContainerInjector, ServiceRunner
from nexus_kit.interfaces import ServiceInterface
from nexus_kit_fastapi import HttpService


@singleton
class Marker(ServiceInterface):
    def start(self) -> None:
        print("MARKER-STARTED", flush=True)

    def stop(self) -> None:
        print("MARKER-STOPPED", flush=True)


@singleton
class Probe(HttpService):
    port = 0
    log_level = "warning"

    def create_app(self) -> FastAPI:
        return FastAPI()


async def main() -> None:
    container = ContainerInjector({})
    async with ServiceRunner(container, [Marker, Probe]):
        service = container.get(Probe)
        print(f"READY {service.bound_port}", flush=True)
        await service.wait()
    print("CLEAN-EXIT", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
