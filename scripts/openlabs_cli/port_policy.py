"""Host port selection for lab lifecycle."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Callable

LOOPBACK = "127.0.0.1"
DYNAMIC_PORT_FLOOR = 30000
DYNAMIC_PORT_CEILING = 39999


@dataclass(frozen=True)
class PortResolution:
    host_port: int
    declared_port: int
    dynamic: bool = False
    error_key: str | None = None
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.error_key is None


def local_port_open(port: int, *, host: str = LOOPBACK) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def pick_free_loopback_port(
    *,
    start: int = DYNAMIC_PORT_FLOOR,
    end: int = DYNAMIC_PORT_CEILING,
    port_open: Callable[[int], bool] | None = None,
) -> int | None:
    probe = port_open or local_port_open
    for port in range(start, end + 1):
        if not probe(port):
            return port
    return None


def resolve_host_port(
    *,
    declared_port: int,
    explicit_port: int | None,
    allow_dynamic: bool = True,
    port_open: Callable[[int], bool] | None = None,
) -> PortResolution:
    probe = port_open or local_port_open
    target = explicit_port if explicit_port is not None else declared_port
    if probe(target):
        if explicit_port is not None:
            return PortResolution(
                host_port=target,
                declared_port=declared_port,
                error_key="lifecycle.port.conflict",
                message=f"port {target} is in use; pick another port or free the listener",
            )
        if not allow_dynamic:
            return PortResolution(
                host_port=target,
                declared_port=declared_port,
                error_key="lifecycle.port.conflict",
                message=f"port {target} is in use; pick another port or free the listener",
            )
        alternate = pick_free_loopback_port(port_open=probe)
        if alternate is None:
            return PortResolution(
                host_port=target,
                declared_port=declared_port,
                error_key="lifecycle.port.conflict",
                message="no free loopback port found in policy range",
            )
        return PortResolution(
            host_port=alternate,
            declared_port=declared_port,
            dynamic=True,
        )
    return PortResolution(host_port=target, declared_port=declared_port)
