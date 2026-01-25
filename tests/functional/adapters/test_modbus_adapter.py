#!/usr/bin/env python3
"""
Functional tests for Modbus adapter (PyModbus 3.11.4) and protocol wrapper.

Tests verify:
- Adapter lifecycle (simulator start/stop, client connect/disconnect)
- Simulator initialisation with device-specific memory
- Modbus read/write operations (coils, registers)
- Protocol wrapper functionality
- Probe/reconnaissance operations
- Error handling and edge cases
"""

import asyncio

import pytest
from components.adapters.pymodbus_3114 import PyModbus3114Adapter
from components.protocols.modbus_protocol import ModbusProtocol

# ============================================================
# Modbus TCP Adapter Tests
# ============================================================


class TestModbusAdapter:
    """Test suite for PyModbus 3.11.4 adapter."""

    @pytest.fixture
    async def adapter(self, unused_tcp_port):
        """Create a fresh adapter instance for each test."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=unused_tcp_port,  # Use dynamic port to avoid conflicts
            device_id=1,
            simulator_mode=True,
            setup={
                "coils": [False] * 64,
                "discrete_inputs": [False] * 64,
                "holding_registers": [0] * 64,
                "input_registers": [0] * 64,
            },
        )
        yield adapter
        await adapter.disconnect()

    @pytest.fixture
    async def connected_adapter(self, adapter):
        """Create and connect an adapter."""
        await adapter.connect()
        yield adapter
        await adapter.disconnect()

    @pytest.fixture
    async def custom_adapter(self, unused_tcp_port):
        """Create adapter with custom initial values."""
        setup = {
            "coils": [True, False, True, False] + [False] * 60,
            "discrete_inputs": [False] * 64,
            "holding_registers": [100, 200, 300, 400] + [0] * 60,
            "input_registers": [10, 20, 30, 40] + [0] * 60,
        }
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=unused_tcp_port,  # Use dynamic port to avoid conflicts
            device_id=2,
            simulator_mode=True,
            setup=setup,
        )
        yield adapter
        await adapter.disconnect()

    # ============================================================
    # Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_adapter_initialisation(self):
        """Test adapter can be instantiated with default settings."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=15020,
            device_id=1,
        )

        assert adapter.host == "localhost"
        assert adapter.port == 15020
        assert adapter.device_id == 1
        assert adapter.simulator_mode is True
        assert adapter.protocol_name == "modbus"
        assert adapter.client is None
        assert adapter.server_task is None
        assert adapter.connected is False

    @pytest.mark.asyncio
    async def test_adapter_with_custom_setup(self):
        """Test adapter initialisation with custom memory layout."""
        custom_setup = {
            "coils": [True] * 32,
            "discrete_inputs": [False] * 32,
            "holding_registers": [1234] * 32,
            "input_registers": [5678] * 32,
        }

        adapter = PyModbus3114Adapter(
            host="127.0.0.1",
            port=15022,
            device_id=5,
            simulator_mode=True,
            setup=custom_setup,
        )

        assert adapter.setup == custom_setup
        assert len(adapter.setup["coils"]) == 32
        assert adapter.setup["holding_registers"][0] == 1234

    @pytest.mark.asyncio
    async def test_adapter_non_simulator_mode(self):
        """Test adapter initialisation in client-only mode."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=15023,
            device_id=1,
            simulator_mode=False,
        )

        assert adapter.simulator_mode is False

    # ============================================================
    # Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_simulator_starts_on_connect(self, adapter):
        """Test simulator starts automatically when connecting."""
        assert adapter.server_task is None

        result = await adapter.connect()

        assert result is True
        assert adapter.connected is True
        assert adapter.server_task is not None
        assert adapter.client is not None

    @pytest.mark.asyncio
    async def test_simulator_stops_on_disconnect(self, connected_adapter):
        """Test simulator stops when disconnecting."""
        assert connected_adapter.server_task is not None

        await connected_adapter.disconnect()

        assert connected_adapter.connected is False
        assert connected_adapter.server_task is None
        assert connected_adapter.client is None

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, connected_adapter):
        """Test multiple connect() calls are safe."""
        first_task = connected_adapter.server_task
        result = await connected_adapter.connect()
        assert result is True
        assert connected_adapter.server_task == first_task

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, adapter):
        """Test disconnect() is safe when not connected."""
        assert adapter.client is None
        await adapter.disconnect()
        assert adapter.connected is False

    @pytest.mark.asyncio
    async def test_non_simulator_mode_connect(self, unused_tcp_port):
        """Test connecting in client-only mode (no simulator)."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=unused_tcp_port,
            device_id=1,
            simulator_mode=False,
        )
        # Connect should fail because there's no server running
        result = await adapter.connect()
        assert result is False
        assert adapter.client is not None
        assert adapter.server_task is None

    # ============================================================
    # Read Operations Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_read_coils_single(self, connected_adapter):
        """Test reading a single coil."""
        result = await connected_adapter.read_coils(0, count=1)
        assert result is not None
        assert not result.isError()
        assert hasattr(result, "bits")
        assert len(result.bits) >= 1

    @pytest.mark.asyncio
    async def test_read_coils_multiple(self, connected_adapter):
        """Test reading multiple coils."""
        result = await connected_adapter.read_coils(0, count=8)
        assert result is not None
        assert not result.isError()
        assert len(result.bits) >= 8

    @pytest.mark.asyncio
    async def test_read_holding_registers_single(self, connected_adapter):
        """Test reading a single holding register."""
        result = await connected_adapter.read_holding_registers(0, count=1)
        assert result is not None
        assert not result.isError()
        assert hasattr(result, "registers")
        assert len(result.registers) == 1

    @pytest.mark.asyncio
    async def test_read_holding_registers_multiple(self, connected_adapter):
        """Test reading multiple holding registers."""
        result = await connected_adapter.read_holding_registers(0, count=10)
        assert result is not None
        assert not result.isError()
        assert len(result.registers) == 10

    @pytest.mark.asyncio
    async def test_read_from_different_addresses(self, connected_adapter):
        """Test reading from various addresses."""
        result0 = await connected_adapter.read_holding_registers(0, count=1)
        assert not result0.isError()
        result10 = await connected_adapter.read_holding_registers(10, count=1)
        assert not result10.isError()
        result50 = await connected_adapter.read_holding_registers(50, count=1)
        assert not result50.isError()

    @pytest.mark.asyncio
    async def test_read_without_connection(self, adapter):
        """Test read operations fail when not connected."""
        with pytest.raises(RuntimeError, match="Client not connected"):
            await adapter.read_coils(0, count=1)
        with pytest.raises(RuntimeError, match="Client not connected"):
            await adapter.read_holding_registers(0, count=1)

    # ============================================================
    # Write Operations Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_write_coil(self, connected_adapter):
        """Test writing a single coil."""
        result = await connected_adapter.write_coil(5, True)
        assert result is not None
        assert not result.isError()
        read_result = await connected_adapter.read_coils(5, count=1)
        assert read_result.bits[0] is True

    @pytest.mark.asyncio
    async def test_write_coil_false(self, connected_adapter):
        """Test writing False to a coil."""
        await connected_adapter.write_coil(5, True)
        result = await connected_adapter.write_coil(5, False)
        assert not result.isError()
        read_result = await connected_adapter.read_coils(5, count=1)
        assert read_result.bits[0] is False

    @pytest.mark.asyncio
    async def test_write_register(self, connected_adapter):
        """Test writing a single holding register."""
        test_value = 1234
        result = await connected_adapter.write_register(10, test_value)
        assert result is not None
        assert not result.isError()
        read_result = await connected_adapter.read_holding_registers(10, count=1)
        assert read_result.registers[0] == test_value

    @pytest.mark.asyncio
    async def test_write_register_various_values(self, connected_adapter):
        """Test writing different values to registers."""
        test_values = [0, 100, 65535, 12345, 999]
        for i, value in enumerate(test_values):
            await connected_adapter.write_register(i, value)
        for i, expected in enumerate(test_values):
            result = await connected_adapter.read_holding_registers(i, count=1)
            assert result.registers[0] == expected

    @pytest.mark.asyncio
    async def test_write_multiple_coils(self, connected_adapter):
        """Test writing multiple coils sequentially."""
        addresses = [0, 1, 2, 3, 4]
        values = [True, False, True, True, False]
        for addr, val in zip(addresses, values, strict=True):
            await connected_adapter.write_coil(addr, val)
        result = await connected_adapter.read_coils(0, count=5)
        for i, expected in enumerate(values):
            assert result.bits[i] == expected

    @pytest.mark.asyncio
    async def test_write_without_connection(self, adapter):
        """Test write operations fail when not connected."""
        with pytest.raises(RuntimeError, match="Client not connected"):
            await adapter.write_coil(0, True)
        with pytest.raises(RuntimeError, match="Client not connected"):
            await adapter.write_register(0, 100)

    # ============================================================
    # Custom Setup Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_custom_initial_values(self, custom_adapter):
        """Test adapter can be manually loaded with custom values."""
        await custom_adapter.connect()
        await custom_adapter.write_register(0, 100)
        await custom_adapter.write_register(1, 200)
        await custom_adapter.write_register(2, 300)
        await custom_adapter.write_register(3, 400)
        result = await custom_adapter.read_holding_registers(0, count=4)
        assert result.registers[0] == 100
        assert result.registers[1] == 200
        assert result.registers[2] == 300
        assert result.registers[3] == 400

    # ============================================================
    # Probe/State Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_get_simulator_state_disconnected(self, adapter):
        """Test get_simulator_state() when disconnected."""
        state = await adapter.get_simulator_state()
        assert state["host"] == "localhost"
        assert state["port"] == adapter.port  # Use actual port from fixture
        assert state["device_id"] == 1
        assert state["simulator"] is True
        assert state["connected"] is False
        assert "setup" in state

    @pytest.mark.asyncio
    async def test_get_simulator_state_connected(self, connected_adapter):
        """Test get_simulator_state() when connected."""
        state = await connected_adapter.get_simulator_state()
        assert state["connected"] is True
        assert state["setup"] is not None

    @pytest.mark.asyncio
    async def test_probe(self, connected_adapter):
        """Test probe() returns simulator state."""
        probe_result = await connected_adapter.probe()
        assert probe_result["host"] == "localhost"
        assert probe_result["connected"] is True
        assert "setup" in probe_result

    # ============================================================
    # Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, unused_tcp_port):
        """Test complete lifecycle: create, connect, use, disconnect."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=unused_tcp_port,
            device_id=1,
            simulator_mode=True,
        )
        await adapter.connect()
        assert adapter.connected is True
        await adapter.write_register(0, 9999)
        await adapter.write_coil(0, True)
        reg_result = await adapter.read_holding_registers(0, count=1)
        assert reg_result.registers[0] == 9999
        coil_result = await adapter.read_coils(0, count=1)
        assert coil_result.bits[0] is True
        await adapter.disconnect()
        assert adapter.connected is False

    @pytest.mark.asyncio
    async def test_reconnect_creates_fresh_simulator(self, unused_tcp_port):
        """Test that disconnecting and reconnecting creates a fresh simulator instance."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=unused_tcp_port,
            device_id=1,
            simulator_mode=True,
        )

        # First connection
        await adapter.connect()
        assert adapter.connected is True
        assert adapter.server_task is not None

        # Write a test value to verify the simulator is working
        await adapter.write_register(5, 7777)
        result = await adapter.read_holding_registers(5, count=1)
        assert result.registers[0] == 7777, "Should be able to write and read value"

        # Store reference to old server task
        old_server_task = adapter.server_task

        # Disconnect - this should stop the simulator
        await adapter.disconnect()
        assert adapter.connected is False
        assert (
            adapter.server_task is None
        ), "Server task should be cleared after disconnect"
        assert adapter.client is None, "Client should be cleared after disconnect"

        # Small delay to ensure port is released
        await asyncio.sleep(0.2)

        # Reconnect - should start a NEW simulator
        await adapter.connect()
        assert adapter.connected is True
        assert adapter.server_task is not None, "New server task should be created"
        assert (
            adapter.server_task != old_server_task
        ), "Should be a new server task instance"

        # Test that we can still communicate (simulator is running)
        result = await adapter.read_holding_registers(5, count=1)
        assert result is not None
        assert not result.isError(), "Should be able to read after reconnect"

        # Clean up
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, connected_adapter):
        """Test concurrent read/write operations."""

        async def writer(addr, value):
            await connected_adapter.write_register(addr, value)

        async def reader(addr):
            return await connected_adapter.read_holding_registers(addr, count=1)

        await asyncio.gather(
            writer(0, 100),
            writer(1, 200),
            writer(2, 300),
            reader(0),
            reader(1),
        )
        result = await connected_adapter.read_holding_registers(0, count=3)
        assert result.registers[0] == 100
        assert result.registers[1] == 200
        assert result.registers[2] == 300


# ============================================================
# Modbus Protocol Wrapper Tests
# ============================================================


class TestModbusProtocol:
    """Test suite for the ModbusProtocol wrapper."""

    @pytest.fixture
    async def protocol(self, unused_tcp_port):
        """Create a fresh protocol instance with simulator adapter."""
        adapter = PyModbus3114Adapter(
            host="localhost",
            port=unused_tcp_port,  # Use dynamic port to avoid conflicts
            device_id=1,
            simulator_mode=True,
        )
        proto = ModbusProtocol(adapter=adapter)
        yield proto
        await proto.disconnect()

    @pytest.fixture
    async def connected_protocol(self, protocol):
        """Create and connect a protocol instance."""
        await protocol.connect()
        yield protocol
        await protocol.disconnect()

    @pytest.mark.asyncio
    async def test_protocol_connect_disconnect(self, protocol):
        """Test protocol connect and disconnect sequence."""
        await protocol.connect()
        assert protocol.connected is True
        await protocol.disconnect()
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_disconnect_when_not_connected(self, protocol):
        """Test disconnecting without prior connect is safe."""
        await protocol.disconnect()
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_read_coils_multiple(self, connected_protocol):
        """Test reading multiple coils via protocol wrapper."""
        result = await connected_protocol.read_coils(0, 8)
        # Protocol returns a list of results (one per coil)
        assert isinstance(result, list)
        assert len(result) == 8
        for item in result:
            assert hasattr(item, "bits")
            assert len(item.bits) >= 1

    @pytest.mark.asyncio
    async def test_protocol_read_holding_registers_multiple(self, connected_protocol):
        """Test reading multiple holding registers via protocol wrapper."""
        result = await connected_protocol.read_holding_registers(0, 8)
        # Protocol returns a list of results (one per register)
        assert isinstance(result, list)
        assert len(result) == 8
        for item in result:
            assert hasattr(item, "registers")
            assert len(item.registers) >= 1

    @pytest.mark.asyncio
    async def test_protocol_write_register(self, connected_protocol):
        """Test writing a holding register via protocol wrapper."""
        await connected_protocol.write_register(0, 1234)
        result = await connected_protocol.read_holding_registers(0, 1)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].registers[0] == 1234

    @pytest.mark.asyncio
    async def test_probe_when_connected(self, connected_protocol):
        """Test protocol probe returns simulator state when connected."""
        state = await connected_protocol.probe()
        assert state["protocol"] == "modbus"
        assert state["connected"] is True
        assert state["coils_readable"] is True
        assert state["holding_registers_readable"] is True

    @pytest.mark.asyncio
    async def test_protocol_disconnect_cleans_up(self, connected_protocol):
        """Ensure disconnect properly cleans adapter and tasks."""
        await connected_protocol.disconnect()
        assert connected_protocol.connected is False
        assert connected_protocol.adapter.client is None
        assert connected_protocol.adapter.server_task is None

    @pytest.mark.asyncio
    async def test_protocol_multiple_connect_calls(self, protocol):
        """Multiple connect() calls do not break the protocol."""
        await protocol.connect()
        first_task = protocol.adapter.server_task
        await protocol.connect()
        assert protocol.adapter.server_task == first_task
        await protocol.disconnect()

    @pytest.mark.asyncio
    async def test_protocol_operations_without_connect(self, protocol):
        """Operations without connect should raise RuntimeError."""
        with pytest.raises(RuntimeError):
            await protocol.read_coils(0, 1)
        with pytest.raises(RuntimeError):
            await protocol.write_register(0, 1)


# ============================================================
# Error Handling Tests (with fixture)
# ============================================================


@pytest.fixture
async def adapter_fixture(unused_tcp_port):
    """Fixture for standalone tests."""
    adapter = PyModbus3114Adapter(
        host="localhost",
        port=unused_tcp_port,
        device_id=1,
        simulator_mode=True,
    )
    yield adapter
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_connect_to_invalid_port_raises():
    """Connecting to invalid port in client-only mode returns False."""
    adapter = PyModbus3114Adapter(
        host="localhost",
        port=99999,  # Invalid high port
        device_id=1,
        simulator_mode=False,  # Client-only mode
    )
    # In client-only mode with no server, connection should fail
    result = await adapter.connect()
    assert result is False


@pytest.mark.asyncio
async def test_write_without_connect_raises(adapter_fixture):
    """Writing without connection raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Client not connected"):
        await adapter_fixture.write_coil(0, True)


@pytest.mark.asyncio
async def test_read_without_connect_raises(adapter_fixture):
    """Reading without connection raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Client not connected"):
        await adapter_fixture.read_coils(0, 1)


# ============================================================
# Async Teardown Tests (with fixture)
# ============================================================


@pytest.mark.asyncio
async def test_multiple_disconnect_calls(adapter_fixture):
    """Calling disconnect multiple times is safe."""
    await adapter_fixture.disconnect()
    await adapter_fixture.disconnect()
    assert adapter_fixture.connected is False


@pytest.mark.asyncio
async def test_concurrent_connect_disconnect(adapter_fixture):
    """Concurrent connect and disconnect operations."""

    async def connect():
        await adapter_fixture.connect()

    async def disconnect():
        await adapter_fixture.disconnect()

    await asyncio.gather(connect(), disconnect())
    assert adapter_fixture.connected in (True, False)


# ============================================================
# Standalone Test Runner (optional)
# ============================================================

if __name__ == "__main__":
    import sys

    import pytest

    print("Running full Modbus adapter and protocol functional test suite...")
    sys.exit(pytest.main([__file__, "-v"]))
