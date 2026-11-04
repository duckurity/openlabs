"""Socket tests for the fixed-upstream SealDesk ingress relay."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

import ingress_proxy as proxy


class IngressTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tasks: set[asyncio.Task[None]] = set()
        self.writers: list[asyncio.StreamWriter] = []
        self.servers: list[asyncio.Server] = []
        self.fixed_config = (
            proxy.LISTEN_HOST,
            proxy.LISTEN_PORT,
            proxy.UPSTREAM_HOST,
            proxy.UPSTREAM_PORT,
            proxy.MAX_CONNECTIONS,
        )
        self.slots = asyncio.Semaphore(1)
        self.patches = [
            patch.object(proxy, "connection_slots", self.slots),
            patch.object(proxy, "UPSTREAM_HOST", "127.0.0.1"),
            patch.object(proxy, "IDLE_TIMEOUT_SECONDS", 2),
        ]
        for item in self.patches:
            item.start()

    def track(self, handler):
        def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            self.writers.append(writer)
            task = asyncio.create_task(handler(reader, writer))
            self.tasks.add(task)
        return connected

    async def asyncTearDown(self) -> None:
        for server in self.servers:
            server.close()
        for writer in self.writers:
            writer.close()
        if self.tasks:
            await asyncio.wait(self.tasks, timeout=1)
        for task in self.tasks:
            if not task.done():
                task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        for writer in self.writers:
            await proxy.close_writer(writer)
        for server in self.servers:
            await server.wait_closed()
        for item in reversed(self.patches):
            item.stop()

    def test_relay_binds_only_the_declared_fixed_upstream_contract(self) -> None:
        self.assertEqual(self.fixed_config, ("0.0.0.0", 8000, "sealdesk", 8000, 64))

    async def test_http_bytes_are_forwarded_only_to_the_fixed_upstream(self) -> None:
        request = (
            b"GET http://outside.invalid/health HTTP/1.1\r\n"
            b"Host: outside.invalid\r\nConnection: close\r\n\r\n"
        )
        observed: list[bytes] = []

        async def upstream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            observed.append(await reader.readexactly(len(request)))
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
            )
            await writer.drain()
            await proxy.close_writer(writer)

        upstream_server = await asyncio.start_server(upstream, "127.0.0.1", 0)
        self.servers.append(upstream_server)
        patch_port = patch.object(
            proxy, "UPSTREAM_PORT", upstream_server.sockets[0].getsockname()[1]
        )
        patch_port.start()
        self.patches.append(patch_port)

        ingress_server = await asyncio.start_server(
            self.track(proxy.handle), "127.0.0.1", 0
        )
        self.servers.append(ingress_server)
        reader, writer = await asyncio.open_connection(
            "127.0.0.1", ingress_server.sockets[0].getsockname()[1]
        )
        self.writers.append(writer)
        writer.write(request)
        await writer.drain()

        response = await asyncio.wait_for(reader.read(), 2)
        self.assertEqual(observed, [request])
        self.assertEqual(
            response,
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok",
        )
        await asyncio.wait_for(self.slots.acquire(), 1)
        self.slots.release()


if __name__ == "__main__":
    unittest.main()
