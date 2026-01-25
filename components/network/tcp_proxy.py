"""
Async TCP proxy with no protocol awareness.
"""

import asyncio


class TCPProxy:
    def __init__(
        self,
        *,
        listen_host: str,
        listen_port: int,
        target_host: str,
        target_port: int,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port

        self.server: asyncio.AbstractServer | None = None

    # ------------------------------------------------------------------

    async def start(self):
        self.server = await asyncio.start_server(
            self._handle,
            self.listen_host,
            self.listen_port,
        )

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    # ------------------------------------------------------------------

    async def _handle(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
    ):
        target_reader, target_writer = await asyncio.open_connection(
            self.target_host,
            self.target_port,
        )

        await asyncio.gather(
            self._pipe(client_reader, target_writer),
            self._pipe(target_reader, client_writer),
        )

    # ------------------------------------------------------------------

    async def _pipe(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        try:
            while data := await reader.read(4096):
                writer.write(data)
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
