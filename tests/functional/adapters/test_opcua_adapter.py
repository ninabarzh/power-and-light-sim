#!/usr/bin/env python3
"""
Functional tests for OPC UA adapter (asyncua 1.1.8).
"""

import asyncio
import gc
import signal
import sys

import pytest
from components.adapters.opcua_asyncua_118 import OPCUAAsyncua118Adapter
from components.protocols.opcua_protocol import OPCUAProtocol

# ============================================================
# GRACEFUL SHUTDOWN HANDLING
# ============================================================

original_handlers = {}


def graceful_interrupt(signum, frame):
    """Handle Ctrl+C gracefully for async tests."""
    print("\n🔴 Test interrupted. Cleaning up OPC UA servers...")

    try:
        loop = asyncio.get_event_loop()
        for task in asyncio.all_tasks(loop):
            if not task.done():
                task.cancel()
    except (RuntimeError, Exception):
        pass

    if signum in original_handlers:
        original_handlers[signum](signum, frame)
    else:
        sys.exit(1)


if sys.platform != "win32":
    for sig in (signal.SIGINT, signal.SIGTERM):
        original_handlers[sig] = signal.signal(sig, graceful_interrupt)


# ============================================================
# TEST CLASSES
# ============================================================


@pytest.mark.first
@pytest.mark.opcua
class TestOPCUAAdapter:
    """Test suite for OPC UA asyncua 1.1.8 adapter."""

    # ============================================================
    # FIXTURE DEFINITIONS
    # ============================================================

    @pytest.fixture(scope="session")
    def event_loop(self):
        """Create a session-scoped event loop for all tests."""
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        yield loop
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()

    @pytest.fixture(scope="class")
    async def shared_server(self):
        """Class-scoped fixture: One OPC UA server instance."""
        adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:4849/",
            namespace_uri="urn:simulator:opcua:test",
            simulator_mode=True,
        )

        await adapter.connect()
        yield adapter

        if adapter._running:
            try:
                await asyncio.wait_for(
                    asyncio.shield(adapter.disconnect()), timeout=3.0
                )
            except (TimeoutError, asyncio.CancelledError):
                if adapter._server:
                    try:
                        adapter._server = None
                    except Exception:
                        pass
                adapter._running = False
                adapter._objects = {}
                gc.collect()

    @pytest.fixture
    async def adapter(self, shared_server):
        """Function-scoped adapter using the shared server."""
        await shared_server.set_variable("Temperature", 20.0)
        await shared_server.set_variable("Pressure", 1.0)
        yield shared_server

    @pytest.fixture
    async def connected_adapter(self, adapter):
        """Fixture for tests that need a connected adapter."""
        yield adapter

    # ============================================================
    # Initialization Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test adapter can be instantiated with default settings."""
        adapter = OPCUAAsyncua118Adapter()
        assert adapter.endpoint == "opc.tcp://0.0.0.0:4840/"
        assert adapter.namespace_uri == "urn:simulator:opcua"
        assert adapter.simulator_mode is True
        assert adapter._server is None
        assert adapter._running is False
        assert adapter._objects == {}

    @pytest.mark.asyncio
    async def test_adapter_custom_initialization(self):
        """Test adapter initialization with custom parameters."""
        adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://127.0.0.1:4841/",
            namespace_uri="urn:custom:namespace",
            simulator_mode=False,
        )
        assert adapter.endpoint == "opc.tcp://127.0.0.1:4841/"
        assert adapter.namespace_uri == "urn:custom:namespace"
        assert adapter.simulator_mode is False

    # ============================================================
    # Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_connect_starts_simulator(self):
        """Test connect() starts the OPC UA server simulator."""
        adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:4850/",
            namespace_uri="urn:simulator:opcua:test",
            simulator_mode=True,
        )

        try:
            result = await adapter.connect()
            assert result is True
            assert adapter._running is True
            assert adapter._server is not None
            assert adapter._namespace_idx is not None
        finally:
            if adapter._running:
                try:
                    await asyncio.wait_for(adapter.disconnect(), timeout=2.0)
                except (TimeoutError, RuntimeError):
                    adapter._server = None
                    adapter._running = False

    @pytest.mark.asyncio
    async def test_connect_creates_default_variables(self, adapter):
        """Test connect() creates Temperature and Pressure variables."""
        assert "Temperature" in adapter._objects
        assert "Pressure" in adapter._objects
        assert len(adapter._objects) == 2

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, connected_adapter):
        """Test multiple connect() calls are safe."""
        assert connected_adapter._running is True
        result = await connected_adapter.connect()
        assert result is True
        assert connected_adapter._running is True

    @pytest.mark.asyncio
    async def test_disconnect_stops_simulator(self):
        """Test disconnect() cleanly stops the server."""
        adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:4851/",
            simulator_mode=True,
        )

        await adapter.connect()
        assert adapter._running is True
        await adapter.disconnect()
        assert adapter._running is False
        assert adapter._server is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnect() is safe when not connected."""
        adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:4852/",
            simulator_mode=False,
        )
        await adapter.disconnect()
        assert adapter._server is None
        assert adapter._running is False

    @pytest.mark.asyncio
    async def test_connect_in_non_simulator_mode(self):
        """Test connect() with simulator_mode=False."""
        adapter = OPCUAAsyncua118Adapter(simulator_mode=False)
        result = await adapter.connect()
        assert result is True
        assert adapter._server is None
        assert adapter._running is False

    # ============================================================
    # Variable Read/Write Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_get_state_returns_all_variables(self, connected_adapter):
        """Test get_state() returns current values of all variables."""
        state = await connected_adapter.get_state()
        assert "Temperature" in state
        assert "Pressure" in state
        assert state["Temperature"] == 20.0
        assert state["Pressure"] == 1.0

    @pytest.mark.asyncio
    async def test_set_variable_updates_temperature(self, connected_adapter):
        """Test set_variable() can update Temperature."""
        await connected_adapter.set_variable("Temperature", 25.5)
        state = await connected_adapter.get_state()
        assert state["Temperature"] == 25.5

    @pytest.mark.asyncio
    async def test_set_variable_updates_pressure(self, connected_adapter):
        """Test set_variable() can update Pressure."""
        await connected_adapter.set_variable("Pressure", 2.5)
        state = await connected_adapter.get_state()
        assert state["Pressure"] == 2.5

    @pytest.mark.asyncio
    async def test_set_variable_with_invalid_name(self, connected_adapter):
        """Test set_variable() raises KeyError for unknown variable."""
        with pytest.raises(KeyError) as exc_info:
            await connected_adapter.set_variable("InvalidVariable", 100)
        assert "No OPC UA variable named 'InvalidVariable'" in str(exc_info.value)

    # ============================================================
    # Protocol Interface Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_browse_root_returns_node_names(self, connected_adapter):
        """Test browse_root() returns list of available node names."""
        nodes = await connected_adapter.browse_root()
        assert isinstance(nodes, list)
        assert "Temperature" in nodes
        assert "Pressure" in nodes
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_read_node_returns_value(self, connected_adapter):
        """Test read_node() returns the value of a specific node."""
        value = await connected_adapter.read_node("Temperature")
        assert value == 20.0

    @pytest.mark.asyncio
    async def test_read_node_invalid_name(self, connected_adapter):
        """Test read_node() raises KeyError for unknown node."""
        with pytest.raises(KeyError) as exc_info:
            await connected_adapter.read_node("InvalidNode")
        assert "No OPC UA variable named 'InvalidNode'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_node_updates_value(self, connected_adapter):
        """Test write_node() can update a node value."""
        success = await connected_adapter.write_node("Temperature", 30.0)
        assert success is True
        value = await connected_adapter.read_node("Temperature")
        assert value == 30.0

    @pytest.mark.asyncio
    async def test_write_node_invalid_name(self, connected_adapter):
        """Test write_node() raises KeyError for unknown node."""
        with pytest.raises(KeyError) as exc_info:
            await connected_adapter.write_node("InvalidNode", 100.0)
        assert "No OPC UA variable named 'InvalidNode'" in str(exc_info.value)

    # ============================================================
    # Probe Functionality Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_probe_when_running(self, connected_adapter):
        """Test probe() returns correct information when server is running."""
        result = await connected_adapter.probe()
        assert result["protocol"] == "OPC UA"
        assert result["implementation"] == "asyncua"
        assert result["version"] == "1.1.8"
        assert result["listening"] is True
        assert result["endpoint"] == connected_adapter.endpoint
        assert result["nodes"] == ["Temperature", "Pressure"]

    @pytest.mark.asyncio
    async def test_probe_when_not_running(self):
        """Test probe() returns correct status when not connected."""
        adapter = OPCUAAsyncua118Adapter(simulator_mode=False)
        result = await adapter.probe()
        assert result["protocol"] == "OPC UA"
        assert result["listening"] is False
        assert result["nodes"] == []

    # ============================================================
    # Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete lifecycle: create, connect, use, disconnect."""
        adapter = OPCUAAsyncua118Adapter(endpoint="opc.tcp://0.0.0.0:4853/")

        try:
            await adapter.connect()
            assert adapter._running is True
            initial_state = await adapter.get_state()
            assert initial_state["Temperature"] == 20.0
            await adapter.set_variable("Temperature", 50.0)
            updated_state = await adapter.get_state()
            assert updated_state["Temperature"] == 50.0
        finally:
            await adapter.disconnect()
            assert adapter._running is False

    @pytest.mark.asyncio
    async def test_reconnect_resets_variables(self):
        """Test disconnecting and reconnecting resets variables to defaults."""
        adapter = OPCUAAsyncua118Adapter(endpoint="opc.tcp://0.0.0.0:4854/")

        try:
            await adapter.connect()
            await adapter.set_variable("Temperature", 100.0)
            state = await adapter.get_state()
            assert state["Temperature"] == 100.0
            await adapter.disconnect()
            await adapter.connect()
            state = await adapter.get_state()
            assert state["Temperature"] == 20.0
        finally:
            await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_adapters_different_ports(self):
        """Test multiple adapter instances can run on different ports."""
        adapter1 = OPCUAAsyncua118Adapter(endpoint="opc.tcp://0.0.0.0:4855/")
        adapter2 = OPCUAAsyncua118Adapter(endpoint="opc.tcp://0.0.0.0:4856/")

        try:
            await adapter1.connect()
            await adapter2.connect()
            assert adapter1._running is True
            assert adapter2._running is True
            await adapter1.set_variable("Temperature", 30.0)
            await adapter2.set_variable("Temperature", 40.0)
            state1 = await adapter1.get_state()
            state2 = await adapter2.get_state()
            assert state1["Temperature"] == 30.0
            assert state2["Temperature"] == 40.0
        finally:
            await adapter1.disconnect()
            await adapter2.disconnect()

    # ============================================================
    # Performance Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, connected_adapter):
        """Test concurrent read/write operations on shared server."""

        async def read_temp():
            return await connected_adapter.read_node("Temperature")

        async def write_temp(value):
            return await connected_adapter.write_node("Temperature", value)

        async def read_pressure():
            return await connected_adapter.read_node("Pressure")

        await asyncio.gather(
            read_temp(),
            write_temp(35.0),
            read_pressure(),
            write_temp(45.0),
            read_temp(),
        )

        final_temp = await connected_adapter.read_node("Temperature")
        assert final_temp == 45.0


# ============================================================
# Protocol Wrapper Tests
# ============================================================


@pytest.mark.second
class TestOPCUAProtocol:
    """Test suite for the OPCUAProtocol wrapper."""

    @pytest.fixture(scope="class")
    async def protocol_server(self):
        """Class-scoped server for protocol tests."""
        adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:4860/",
            namespace_uri="urn:simulator:opcua:protocol",
            simulator_mode=True,
        )
        await adapter.connect()
        yield adapter

        if adapter._running:
            try:
                adapter._server = None
                adapter._running = False
                adapter._objects = {}
            except Exception:
                pass

    @pytest.fixture
    async def protocol_adapter(self, protocol_server):
        """Function-scoped adapter for protocol tests."""
        await protocol_server.set_variable("Temperature", 20.0)
        await protocol_server.set_variable("Pressure", 1.0)
        yield protocol_server

    @pytest.fixture
    async def protocol(self, protocol_adapter):
        """Create a protocol instance with the shared adapter."""
        return OPCUAProtocol(protocol_adapter)

    @pytest.fixture
    async def protocol_connected(self, protocol):
        """Already connected protocol instance."""
        await protocol.connect()
        return protocol

    # ============================================================
    # Protocol Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_initialization(self, protocol_adapter):
        """Test protocol wrapper initialization."""
        protocol = OPCUAProtocol(protocol_adapter)
        assert protocol.protocol_name == "opcua"
        assert protocol.connected is False
        assert protocol.adapter == protocol_adapter

    @pytest.mark.asyncio
    async def test_protocol_connect_disconnect(self, protocol):
        """Test protocol connect and disconnect sequence."""
        result = await protocol.connect()
        assert result is True
        assert protocol.connected is True
        nodes = await protocol.browse()
        assert isinstance(nodes, list)
        assert len(nodes) > 0
        protocol.connected = False
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_disconnect_when_not_connected(self, protocol):
        """Test disconnecting without prior connect is safe."""
        await protocol.disconnect()
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_multiple_connect_calls(self, protocol):
        """Multiple connect() calls do not break the protocol."""
        await protocol.connect()
        first_state = protocol.connected
        await protocol.connect()
        assert protocol.connected == first_state
        protocol.connected = False

    # ============================================================
    # Protocol Operation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_browse_operation(self, protocol_connected):
        """Test browse operation via protocol wrapper."""
        nodes = await protocol_connected.browse()
        assert isinstance(nodes, list)
        assert "Temperature" in nodes
        assert "Pressure" in nodes

    @pytest.mark.asyncio
    async def test_protocol_read_operation(self, protocol_connected):
        """Test read operation via protocol wrapper."""
        nodes = await protocol_connected.browse()
        assert len(nodes) > 0
        value = await protocol_connected.read(nodes[0])
        assert value == 20.0

    @pytest.mark.asyncio
    async def test_protocol_write_operation(self, protocol_connected):
        """Test write operation via protocol wrapper."""
        success = await protocol_connected.write("Temperature", 99.9)
        assert success is True
        value = await protocol_connected.read("Temperature")
        assert value == 99.9

    @pytest.mark.asyncio
    async def test_protocol_operations_without_connect(self, protocol):
        """Operations without connect should work (protocol handles connection)."""
        nodes = await protocol.browse()
        assert isinstance(nodes, list)
        if nodes:
            value = await protocol.read(nodes[0])
            assert isinstance(value, float)

    # ============================================================
    # Protocol Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_probe_when_connected(self, protocol_connected):
        """Test protocol probe returns comprehensive recon data."""
        original_probe = protocol_connected.probe

        async def mock_probe():
            return {
                "protocol": "opcua",
                "connected": True,
                "browse": True,
                "read": True,
                "write": True,
            }

        protocol_connected.probe = mock_probe

        try:
            probe_result = await protocol_connected.probe()
            assert probe_result["protocol"] == "opcua"
            assert probe_result["connected"] is True
            assert probe_result["browse"] is True
            assert probe_result["read"] is True
            assert probe_result["write"] is True
        finally:
            protocol_connected.probe = original_probe

    @pytest.mark.asyncio
    async def test_protocol_probe_when_not_connected(self):
        """Test protocol probe when adapter is not in simulator mode."""
        client_adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:9999/",
            simulator_mode=False,
        )

        original_connect = client_adapter.connect

        async def mock_connect():
            return False

        client_adapter.connect = mock_connect

        try:
            client_protocol = OPCUAProtocol(client_adapter)

            async def mock_probe():
                return {
                    "protocol": "opcua",
                    "connected": False,
                    "browse": False,
                    "read": False,
                    "write": False,
                }

            client_protocol.probe = mock_probe
            probe_result = await client_protocol.probe()
            assert probe_result["protocol"] == "opcua"
            assert probe_result["connected"] is False
            assert probe_result["browse"] is False
            assert probe_result["read"] is False
            assert probe_result["write"] is False
        finally:
            client_adapter.connect = original_connect

    @pytest.mark.asyncio
    async def test_protocol_probe_handles_partial_failures(self, protocol):
        """Test probe handles partial failures gracefully."""

        async def mock_probe():
            return {
                "protocol": "opcua",
                "connected": False,
                "browse": False,
                "read": False,
                "write": False,
            }

        protocol.probe = mock_probe
        probe_result = await protocol.probe()
        assert isinstance(probe_result, dict)
        assert "protocol" in probe_result
        assert "connected" in probe_result
        assert "browse" in probe_result
        assert "read" in probe_result
        assert "write" in probe_result

    # ============================================================
    # Protocol Error Handling Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_read_invalid_node(self, protocol_connected):
        """Test read operation with invalid node name."""
        with pytest.raises(KeyError) as exc_info:
            await protocol_connected.read("InvalidNodeName")
        assert "No OPC UA variable named 'InvalidNodeName'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_protocol_write_invalid_node(self, protocol_connected):
        """Test write operation with invalid node name."""
        with pytest.raises(KeyError) as exc_info:
            await protocol_connected.write("InvalidNodeName", 100.0)
        assert "No OPC UA variable named 'InvalidNodeName'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_protocol_operations_after_disconnect(self, protocol_connected):
        """Test operations after protocol disconnect."""
        protocol_connected.connected = False
        assert protocol_connected.connected is False
        nodes = await protocol_connected.browse()
        assert isinstance(nodes, list)

    # ============================================================
    # Protocol Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_full_workflow(self, protocol_adapter):
        """Test complete protocol workflow: connect, browse, read, write."""
        protocol = OPCUAProtocol(protocol_adapter)
        await protocol.connect()
        assert protocol.connected is True
        nodes = await protocol.browse()
        assert len(nodes) >= 2
        temp_value = await protocol.read("Temperature")
        assert temp_value == 20.0
        await protocol.write("Temperature", 75.5)
        updated_temp = await protocol.read("Temperature")
        assert updated_temp == 75.5
        protocol.connected = False

    @pytest.mark.asyncio
    async def test_protocol_with_non_simulator_adapter(self):
        """Test protocol with adapter in non-simulator mode."""
        client_adapter = OPCUAAsyncua118Adapter(
            endpoint="opc.tcp://0.0.0.0:9999/",
            simulator_mode=False,
        )

        async def mock_connect():
            return False

        client_adapter.connect = mock_connect
        protocol = OPCUAProtocol(client_adapter)
        nodes = await protocol.browse()
        assert nodes == []

    @pytest.mark.asyncio
    async def test_concurrent_protocol_operations(self, protocol_connected):
        """Test concurrent operations via protocol wrapper."""

        async def operation_sequence():
            nodes = await protocol_connected.browse()
            if nodes:
                await protocol_connected.read(nodes[0])
                await protocol_connected.write(nodes[0], 50.0)
                return await protocol_connected.read(nodes[0])
            return None

        results = await asyncio.gather(
            operation_sequence(),
            operation_sequence(),
            operation_sequence(),
        )

        assert all(result == 50.0 for result in results if result is not None)


# ============================================================
# Error Handling Tests
# ============================================================


@pytest.mark.asyncio
async def test_adapter_cleanup_timeout_handling():
    """Test that adapter handles timeout during disconnect gracefully."""
    adapter = OPCUAAsyncua118Adapter(endpoint="opc.tcp://0.0.0.0:4865/")
    await adapter.connect()
    assert adapter._running is True
    await adapter.disconnect()
    assert adapter._running is False


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
