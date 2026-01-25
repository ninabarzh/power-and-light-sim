"""
Async protocol socket dispatcher.

Owns:
- TCP listeners
- Network enforcement
- Delegation to protocol handlers
"""

import asyncio

from components.network.network_simulator import NetworkSimulator


class ProtocolSimulator:
    def __init__(self, network: NetworkSimulator):
        self.network = network
        self.listeners: list[_Listener] = []

    # ------------------------------------------------------------------

    async def register(
        self,
        *,
        node: str,
        network: str,
        port: int,
        protocol: str,
        handler_factory,
    ):
        await self.network.expose_service(node, protocol, port)

        self.listeners.append(
            _Listener(
                node=node,
                network=network,
                port=port,
                protocol=protocol,
                handler_factory=handler_factory,
                network_sim=self.network,
            )
        )

    # ------------------------------------------------------------------

    async def start(self):
        await asyncio.gather(*(listener.start() for listener in self.listeners))

    async def stop(self):
        await asyncio.gather(*(listener.stop() for listener in self.listeners))


# ======================================================================


class _Listener:
    def __init__(
        self,
        *,
        node: str,
        network: str,
        port: int,
        protocol: str,
        handler_factory,
        network_sim: NetworkSimulator,
    ):
        self.node = node
        self.network = network
        self.port = port
        self.protocol = protocol
        self.handler_factory = handler_factory
        self.network_sim = network_sim

        self.server: asyncio.AbstractServer | None = None

    # ------------------------------------------------------------------

    async def start(self):
        self.server = await asyncio.start_server(
            self._handle,
            host="0.0.0.0",
            port=self.port,
        )

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    # ------------------------------------------------------------------

    async def _handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        # For now, attacker always comes from corporate network
        src_network = "corporate_network"

        allowed = await self.network_sim.can_reach(
            src_network,
            self.node,
            self.protocol,
            self.port,
        )

        if not allowed:
            writer.close()
            await writer.wait_closed()
            return

        handler = self.handler_factory()
        await handler.serve(reader, writer)
