"""Bounded TCP ingress adapted from OpenLabs Firmdrama (Apache-2.0)."""
from __future__ import annotations

import asyncio
import os

UPSTREAM_HOST = os.getenv("LAST_REEL_UPSTREAM_HOST", "last-reel")
UPSTREAM_PORT = 8000
MAX_CONNECTIONS = 32
IDLE_TIMEOUT = 10
CONNECT_TIMEOUT = 3
slots = asyncio.Semaphore(MAX_CONNECTIONS)


async def close(writer):
    writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), CONNECT_TIMEOUT)
    except (ConnectionError, OSError, TimeoutError):
        writer.transport.abort()


async def forward(reader, writer):
    while True:
        data = await asyncio.wait_for(reader.read(16384), IDLE_TIMEOUT)
        if not data:
            return True
        writer.write(data)
        await asyncio.wait_for(writer.drain(), IDLE_TIMEOUT)


async def handle(client_reader, client_writer):
    acquired = False
    upstream_writer = None
    tasks = []
    try:
        try:
            await asyncio.wait_for(slots.acquire(), 0.05)
            acquired = True
        except TimeoutError:
            return
        upstream_reader, upstream_writer = await asyncio.wait_for(asyncio.open_connection(UPSTREAM_HOST, UPSTREAM_PORT), CONNECT_TIMEOUT)
        tasks = [asyncio.create_task(forward(client_reader, upstream_writer)), asyncio.create_task(forward(upstream_reader, client_writer))]
        completed, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        request_task, response_task = tasks
        if response_task not in completed and request_task.result():
            upstream_writer.write_eof()
            await asyncio.wait_for(upstream_writer.drain(), IDLE_TIMEOUT)
            await asyncio.wait_for(response_task, IDLE_TIMEOUT)
    except (ConnectionError, OSError, TimeoutError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if upstream_writer is not None:
            await close(upstream_writer)
        await close(client_writer)
        if acquired:
            slots.release()


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", 8000, limit=16384)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
