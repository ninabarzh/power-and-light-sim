#!/usr/bin/env python3
"""
OPC UA adapter using asyncua 1.1.8.

- Uses asyncua.Server as a real OPC UA simulator
- Fully asyncio-native
- Exposes a clean async lifecycle for the simulator manager
"""

from asyncua import Server


class OPCUAAsyncua118Adapter:
    """Async OPC UA simulator adapter (asyncua 1.1.8)."""

    def __init__(
        self,
        endpoint="opc.tcp://0.0.0.0:4840/",
        namespace_uri="urn:simulator:opcua",
        simulator_mode=True,
    ):
        self.endpoint = endpoint
        self.namespace_uri = namespace_uri
        self.simulator_mode = simulator_mode

        self._server = None
        self._namespace_idx = None
        self._objects = {}
        self._running = False

    # ------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Start OPC UA simulator.
        """
        if self._running or not self.simulator_mode:
            return True

        self._server = Server()
        await self._server.init()

        self._server.set_endpoint(self.endpoint)
        self._server.set_server_name("AsyncUA OPC UA Simulator")

        self._namespace_idx = await self._server.register_namespace(self.namespace_uri)

        objects = self._server.nodes.objects
        sim_obj = await objects.add_object(self._namespace_idx, "Simulator")

        temperature = await sim_obj.add_variable(
            self._namespace_idx, "Temperature", 20.0
        )
        pressure = await sim_obj.add_variable(self._namespace_idx, "Pressure", 1.0)

        await temperature.set_writable()
        await pressure.set_writable()

        self._objects["Temperature"] = temperature
        self._objects["Pressure"] = pressure

        await self._server.start()
        self._running = True
        return True

    async def disconnect(self) -> None:
        """
        Stop OPC UA simulator.
        """
        if not self._server:
            return

        await self._server.stop()
        self._server = None
        self._objects = {}  # Clear objects on disconnect
        self._running = False

    # ------------------------------------------------------------
    # async-facing helpers
    # ------------------------------------------------------------

    async def probe(self):
        """
        Minimal recon output.
        """
        return {
            "protocol": "OPC UA",
            "implementation": "asyncua",
            "version": "1.1.8",
            "listening": self._running,
            "endpoint": self.endpoint,
            "nodes": list(self._objects.keys()),
        }

    async def get_state(self):
        """
        Return current simulated variable state.
        """
        state = {}
        for name, node in self._objects.items():
            state[name] = await node.read_value()
        return state

    async def set_variable(self, name, value):
        """
        Set a simulated OPC UA variable.
        """
        node = self._objects.get(name)
        if not node:
            raise KeyError(f"No OPC UA variable named '{name}'")

        # Convert value to float to match the variable type
        # (Temperature and Pressure are initialized as floats)
        await node.write_value(float(value))

    # ------------------------------------------------------------
    # Protocol interface methods (for OPCUAProtocol)
    # ------------------------------------------------------------

    async def browse_root(self):
        """
        Browse root nodes (returns list of node names).
        Required by OPCUAProtocol.
        """
        if not self._running:
            return []
        return list(self._objects.keys())

    async def read_node(self, node_id):
        """
        Read a node value by name.
        Required by OPCUAProtocol.
        """
        if not self._running:
            raise RuntimeError("Server not running")

        node = self._objects.get(node_id)
        if not node:
            raise KeyError(f"No OPC UA variable named '{node_id}'")

        return await node.read_value()

    async def write_node(self, node_id, value):
        """
        Write a node value by name.
        Required by OPCUAProtocol.
        """
        if not self._running:
            raise RuntimeError("Server not running")

        node = self._objects.get(node_id)
        if not node:
            raise KeyError(f"No OPC UA variable named '{node_id}'")

        # Convert to float to match variable type
        await node.write_value(float(value))
        return True
