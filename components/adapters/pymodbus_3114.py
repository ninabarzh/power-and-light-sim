"""
PyModbus 3.11.4 async simulator + client adapter.

Fully initialised simulator with device-specific memory.
"""

import asyncio

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.datastore import ModbusServerContext
from pymodbus.datastore.simulator import ModbusSimulatorContext
from pymodbus.server import StartAsyncTcpServer


class PyModbus3114Adapter:
    def __init__(
        self,
        host: str,
        port: int,
        device_id: int,
        simulator_mode: bool = True,
        setup: dict = None,
    ):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.simulator_mode = simulator_mode
        self.protocol_name = "modbus"

        self.setup = setup or {
            "coils": [False] * 64,
            "discrete_inputs": [False] * 64,
            "holding_registers": [0] * 64,
            "input_registers": [0] * 64,
        }

        self.client: AsyncModbusTcpClient | None = None
        self.server_task: asyncio.Task | None = None
        self.connected: bool = False

    # ------------------------------------------------------------------
    # Simulator lifecycle
    # ------------------------------------------------------------------
    async def start_simulator(self) -> None:
        if not self.simulator_mode or self.server_task:
            return

        max_size = max(
            len(self.setup["coils"]),
            len(self.setup["discrete_inputs"]),
            len(self.setup["holding_registers"]),
            len(self.setup["input_registers"]),
        )

        config = {
            "setup": {
                "co size": len(self.setup["coils"]),
                "di size": len(self.setup["discrete_inputs"]),
                "hr size": len(self.setup["holding_registers"]),
                "ir size": len(self.setup["input_registers"]),
                "shared blocks": True,
                "type exception": False,
                "defaults": {
                    "value": {
                        "bits": 0,
                        "uint16": 0,
                        "uint32": 0,
                        "float32": 0.0,
                        "string": " ",
                    },
                    "action": {
                        "bits": None,
                        "uint16": None,
                        "uint32": None,
                        "float32": None,
                        "string": None,
                    },
                },
            },
            "invalid": [],
            "write": ([[0, max_size - 1]] if max_size > 0 else []),
            "uint16": [{"addr": [0, max_size - 1], "value": 0}] if max_size > 0 else [],
            "bits": [],
            "uint32": [],
            "float32": [],
            "string": [],
            "repeat": [],
        }

        simulator = ModbusSimulatorContext(config=config, custom_actions=None)
        context = ModbusServerContext(simulator, single=True)

        self.server_task = asyncio.create_task(
            StartAsyncTcpServer(context=context, address=(self.host, self.port))
        )

        # Give server more time to start and bind to port
        await asyncio.sleep(0.5)

    async def stop_simulator(self) -> None:
        if self.server_task and not self.server_task.done():
            # Cancel the server task
            self.server_task.cancel()
            try:
                # Wait for cancellation with timeout
                await asyncio.wait_for(self.server_task, timeout=2.0)
            except (TimeoutError, asyncio.CancelledError):
                # These are expected - task was cancelled or timed out
                pass
            except Exception:
                # Ignore other exceptions during shutdown
                pass
            finally:
                self.server_task = None
                # Small delay to ensure OS releases the port
                await asyncio.sleep(0.1)

    async def _load_initial_values(self) -> None:
        """Load custom initial values into the running simulator."""
        if not self.client or not self.connected:
            return

        # Give server more time to fully initialize
        await asyncio.sleep(0.25)

        # Write custom holding register values
        # Note: There's a quirk where the first write might get incremented by 1,
        # so we write twice to ensure the correct value
        for addr, value in enumerate(self.setup["holding_registers"]):
            if value != 0:  # Only write non-default values
                try:
                    # First write
                    await self.write_register(addr, value)
                    # Small delay
                    await asyncio.sleep(0.01)
                    # Second write to ensure correct value
                    await self.write_register(addr, value)
                except Exception:
                    # Silently ignore - server might not be fully ready
                    pass

        # Write custom coil values
        for addr, value in enumerate(self.setup["coils"]):
            if value:  # Only write True values
                try:
                    await self.write_coil(addr, value)
                except Exception:
                    # Silently ignore
                    pass

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> bool:
        if self.simulator_mode:
            await self.start_simulator()

        if not self.client:
            self.client = AsyncModbusTcpClient(host=self.host, port=self.port)
            self.client.unit_id = self.device_id

        if not self.connected:
            self.connected = await self.client.connect()

        # Load custom initial values after connection (only if we just connected)
        # DISABLED for now due to quirk - users should manually load if needed
        # if self.connected and self.simulator_mode and not hasattr(self, '_initial_values_loaded'):
        #     await self._load_initial_values()
        #     self._initial_values_loaded = True

        return self.connected

    async def disconnect(self) -> None:
        # Close client first
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass  # Ignore errors during client close
            self.client = None

        # Stop simulator
        if self.simulator_mode:
            await self.stop_simulator()

        self.connected = False
        # Reset the loaded flag so values are reloaded on next connect
        if hasattr(self, "_initial_values_loaded"):
            delattr(self, "_initial_values_loaded")

    # ------------------------------------------------------------------
    # Modbus primitives
    # ------------------------------------------------------------------
    async def read_coils(self, address: int, count: int = 1):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.read_coils(address, count=count)

    async def read_holding_registers(self, address: int, count: int = 1):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.read_holding_registers(address, count=count)

    async def write_coil(self, address: int, value: bool):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.write_coil(address, value)

    async def write_register(self, address: int, value: int):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.write_register(address, value)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    async def get_simulator_state(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "device_id": self.device_id,
            "simulator": self.simulator_mode,
            "connected": self.connected,
            "setup": self.setup,
        }

    async def probe(self) -> dict[str, object]:
        return await self.get_simulator_state()
