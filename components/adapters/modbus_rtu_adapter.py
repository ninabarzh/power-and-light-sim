"""
Modbus RTU adapter using pymodbus 3.11.4

Supports serial communication for RTU devices.
"""

import asyncio

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.datastore import ModbusServerContext
from pymodbus.datastore.simulator import ModbusSimulatorContext
from pymodbus.server import StartAsyncSerialServer


class ModbusRTUAdapter:
    def __init__(
        self,
        port: str,
        device_id: int,
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        simulator_mode: bool = True,
        setup: dict | None = None,
    ):
        self.port = port
        self.device_id = device_id
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.simulator_mode = simulator_mode

        # Keep device array-style memory
        self.setup = setup or {
            "coils": [False] * 64,
            "discrete_inputs": [False] * 64,
            "holding_registers": [0] * 64,
            "input_registers": [0] * 64,
        }

        self.client: AsyncModbusSerialClient | None = None
        self.server_task: asyncio.Task | None = None
        self.connected: bool = False

    # ------------------------------------------------------------------
    # Simulator lifecycle
    # ------------------------------------------------------------------
    async def start_simulator(self) -> None:
        if not self.simulator_mode or self.server_task:
            return

        # Calculate max size for shared memory
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
            "write": [[0, max_size - 1]] if max_size > 0 else [],
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
            StartAsyncSerialServer(
                context=context,
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
            )
        )

        await asyncio.sleep(0.3)

    async def stop_simulator(self) -> None:
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            self.server_task = None

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> bool:
        if self.simulator_mode:
            await self.start_simulator()

        if not self.client:
            self.client = AsyncModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
            )
            self.client.unit_id = self.device_id

        if not self.connected:
            self.connected = await self.client.connect()

        return self.connected

    async def disconnect(self) -> None:
        if self.client:
            self.client.close()
            self.client = None

        if self.simulator_mode:
            await self.stop_simulator()

        self.connected = False

    # ------------------------------------------------------------------
    # Modbus RTU primitives
    # ------------------------------------------------------------------
    async def read_coils(self, address: int, count: int = 1):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.read_coils(address, count=count)

    async def read_discrete_inputs(self, address: int, count: int = 1):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.read_discrete_inputs(address, count=count)

    async def read_holding_registers(self, address: int, count: int = 1):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.read_holding_registers(address, count=count)

    async def read_input_registers(self, address: int, count: int = 1):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.read_input_registers(address, count=count)

    async def write_coil(self, address: int, value: bool):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.write_coil(address, value)

    async def write_register(self, address: int, value: int):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.write_register(address, value)

    async def write_multiple_coils(self, address: int, values: list[bool]):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.write_coils(address, values)

    async def write_multiple_registers(self, address: int, values: list[int]):
        if not self.client:
            raise RuntimeError("Client not connected")
        return await self.client.write_registers(address, values)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    async def get_device_info(self) -> dict:
        """Read Modbus device identification"""
        if not self.client:
            raise RuntimeError("Client not connected")

        try:
            result = await self.client.read_device_information()
            if hasattr(result, "information"):
                return result.information
            return {}
        except Exception:
            return {}

    async def probe(self) -> dict:
        return {
            "port": self.port,
            "device_id": self.device_id,
            "baudrate": self.baudrate,
            "simulator": self.simulator_mode,
            "connected": self.connected,
            "setup": self.setup,
        }
