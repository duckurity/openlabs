"""Bounded TCP ingress for the isolated SealDesk application service."""

from __future__ import annotations

import asyncio

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8000
UPSTREAM_HOST = "sealdesk"
UPSTREAM_PORT = 8000
MAX_CONNECTIONS = 64
IDLE_TIMEOUT_SECONDS = 30.0
CONNECT_TIMEOUT_SECONDS = 3.0

connection_slots = asyncio.Semaphore(MAX_CONNECTIONS)


async def close_writer(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), CONNECT_TIMEOUT_SECONDS)
    except (ConnectionError, OSError, TimeoutError):
        writer.transport.abort()


async def forward(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
    while True:
        data = await asyncio.wait_for(reader.read(65536), IDLE_TIMEOUT_SECONDS)
        if not data:
            return True
        writer.write(data)
        await asyncio.wait_for(writer.drain(), IDLE_TIMEOUT_SECONDS)


async def handle(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
) -> None:
    acquired = False
    upstream_writer: asyncio.StreamWriter | None = None
    forwarding_tasks: list[asyncio.Task[bool]] = []
    try:
        try:
            await asyncio.wait_for(connection_slots.acquire(), timeout=0.05)
            acquired = True
        except TimeoutError:
            return

        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(UPSTREAM_HOST, UPSTREAM_PORT),
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
        forwarding_tasks = [
            asyncio.create_task(forward(client_reader, upstream_writer)),
            asyncio.create_task(forward(upstream_reader, client_writer)),
        ]
        completed, _ = await asyncio.wait(
            forwarding_tasks, return_when=asyncio.FIRST_COMPLETED
        )
        request_task, response_task = forwarding_tasks
        # Preserve response delivery when the client half-closes its request.
        if response_task not in completed and request_task.result():
            upstream_writer.write_eof()
            await asyncio.wait_for(upstream_writer.drain(), IDLE_TIMEOUT_SECONDS)
            await asyncio.wait_for(response_task, IDLE_TIMEOUT_SECONDS)
    except (ConnectionError, OSError, TimeoutError):
        pass
    finally:
        for task in forwarding_tasks:
            task.cancel()
        if forwarding_tasks:
            await asyncio.gather(*forwarding_tasks, return_exceptions=True)
        if upstream_writer is not None:
            await close_writer(upstream_writer)
        await close_writer(client_writer)
        if acquired:
            connection_slots.release()


async def main() -> None:
    server = await asyncio.start_server(handle, LISTEN_HOST, LISTEN_PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
