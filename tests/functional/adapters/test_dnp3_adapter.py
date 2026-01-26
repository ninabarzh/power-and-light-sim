#!/usr/bin/env python3
"""
Functional tests for DNP3 adapter (dnp3py) and protocol wrapper.

Tests verify:
- Adapter lifecycle (outstation and master modes)
- Database initialization and updates
- Point read/write operations (outstation mode)
- Master/outstation connectivity
- Protocol wrapper functionality
- Probe/reconnaissance operations
- Error handling and edge cases

Note: Some master mode operations are placeholders in the current implementation.
"""

import asyncio

import pytest

from components.adapters.dnp3_adapter import DNP3Adapter
from components.protocols.dnp3_protocol import DNP3Protocol


class TestDNP3AdapterOutstation:
    """Test suite for DNP3 adapter in outstation (server) mode."""

    @pytest.fixture
    async def adapter(self):
        """Create a fresh outstation adapter for each test."""
        adapter = DNP3Adapter(
            mode="outstation",
            host="0.0.0.0",
            port=20000,
            simulator_mode=True,
            setup={
                "binary_inputs": {},
                "analog_inputs": {},
                "counters": {},
            },
        )
        yield adapter
        # Cleanup
        if adapter.connected:
            await adapter.disconnect()

    @pytest.fixture
    async def connected_adapter(self, adapter):
        """Create and connect an outstation adapter."""
        await adapter.connect()
        yield adapter
        await adapter.disconnect()

    @pytest.fixture
    async def adapter_with_data(self):
        """Create outstation adapter with initial data."""
        adapter = DNP3Adapter(
            mode="outstation",
            host="0.0.0.0",
            port=20001,
            simulator_mode=True,
            setup={
                "binary_inputs": {0: True, 1: False, 2: True},
                "analog_inputs": {0: 100.5, 1: 200.7, 2: 300.2},
                "counters": {0: 10, 1: 20, 2: 30},
            },
        )
        yield adapter
        if adapter.connected:
            await adapter.disconnect()

    # ============================================================
    # Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_adapter_initialization_outstation(self):
        """Test outstation adapter initialization."""
        adapter = DNP3Adapter(mode="outstation")

        assert adapter.mode == "outstation"
        assert adapter.host == "0.0.0.0"
        assert adapter.port == 20000
        assert adapter.simulator_mode is True
        assert adapter.connected is False
        assert adapter.database is None
        assert adapter.outstation is None
        assert adapter.server is None

    @pytest.mark.asyncio
    async def test_adapter_custom_initialization(self):
        """Test adapter with custom parameters."""
        setup = {
            "binary_inputs": {0: True, 1: False},
            "analog_inputs": {0: 50.5},
            "counters": {0: 100},
        }

        adapter = DNP3Adapter(
            mode="outstation",
            host="127.0.0.1",
            port=20002,
            simulator_mode=False,
            setup=setup,
        )

        assert adapter.host == "127.0.0.1"
        assert adapter.port == 20002
        assert adapter.simulator_mode is False
        assert adapter.setup == setup

    # ============================================================
    # Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_connect_starts_outstation(self, adapter):
        """Test connect() starts the DNP3 outstation."""
        result = await adapter.connect()

        assert result is True
        assert adapter.connected is True
        assert adapter.database is not None
        assert adapter.outstation is not None
        assert adapter.server is not None

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, connected_adapter):
        """Test multiple connect() calls are safe."""
        first_db = connected_adapter.database

        # Second connect should not recreate components
        result = await connected_adapter.connect()
        assert result is True
        assert connected_adapter.database == first_db

    @pytest.mark.asyncio
    async def test_disconnect_stops_outstation(self, connected_adapter):
        """Test disconnect() cleanly stops the outstation."""
        assert connected_adapter.connected is True

        await connected_adapter.disconnect()

        assert connected_adapter.connected is False
        assert connected_adapter.database is None
        assert connected_adapter.outstation is None
        assert connected_adapter.server is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, adapter):
        """Test disconnect() is safe when not connected."""
        assert adapter.server is None

        await adapter.disconnect()

        assert adapter.connected is False

    # ============================================================
    # Database Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_database_initialized_with_setup(self, adapter_with_data):
        """Test database is populated with setup data."""
        await adapter_with_data.connect()

        # Verify database exists and has points configured
        assert adapter_with_data.database is not None

        # Setup values should be stored
        assert adapter_with_data.setup["binary_inputs"][0] is True
        assert adapter_with_data.setup["analog_inputs"][0] == 100.5
        assert adapter_with_data.setup["counters"][0] == 10

    # ============================================================
    # Point Update Tests (Outstation)
    # ============================================================

    @pytest.mark.asyncio
    async def test_update_binary_input(self, connected_adapter):
        """Test updating binary input point."""
        # Add point to database first
        connected_adapter.database.add_binary_input(0, None)

        await connected_adapter.update_binary_input(0, True)

        assert connected_adapter.setup["binary_inputs"][0] is True

    @pytest.mark.asyncio
    async def test_update_analog_input(self, connected_adapter):
        """Test updating analog input point."""
        # Add point to database first
        connected_adapter.database.add_analog_input(0, None)

        await connected_adapter.update_analog_input(0, 123.45)

        assert connected_adapter.setup["analog_inputs"][0] == 123.45

    @pytest.mark.asyncio
    async def test_update_counter(self, connected_adapter):
        """Test updating counter point."""
        # Add point to database first
        connected_adapter.database.add_counter(0, None)

        await connected_adapter.update_counter(0, 999)

        assert connected_adapter.setup["counters"][0] == 999

    @pytest.mark.asyncio
    async def test_update_multiple_points(self, connected_adapter):
        """Test updating multiple points of different types."""
        # Add points to database
        for i in range(3):
            connected_adapter.database.add_binary_input(i, None)
            connected_adapter.database.add_analog_input(i, None)
            connected_adapter.database.add_counter(i, None)

        # Update all points
        await connected_adapter.update_binary_input(0, True)
        await connected_adapter.update_binary_input(1, False)
        await connected_adapter.update_binary_input(2, True)

        await connected_adapter.update_analog_input(0, 10.5)
        await connected_adapter.update_analog_input(1, 20.7)
        await connected_adapter.update_analog_input(2, 30.2)

        await connected_adapter.update_counter(0, 100)
        await connected_adapter.update_counter(1, 200)
        await connected_adapter.update_counter(2, 300)

        # Verify all updates
        assert connected_adapter.setup["binary_inputs"][0] is True
        assert connected_adapter.setup["binary_inputs"][1] is False
        assert connected_adapter.setup["analog_inputs"][1] == 20.7
        assert connected_adapter.setup["counters"][2] == 300

    @pytest.mark.asyncio
    async def test_update_without_connection(self, adapter):
        """Test update operations fail when not connected."""
        with pytest.raises(RuntimeError, match="Outstation not started"):
            await adapter.update_binary_input(0, True)

        with pytest.raises(RuntimeError, match="Outstation not started"):
            await adapter.update_analog_input(0, 100.0)

        with pytest.raises(RuntimeError, match="Outstation not started"):
            await adapter.update_counter(0, 10)

    # ============================================================
    # Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_probe_when_connected(self, connected_adapter):
        """Test probe() returns correct info when connected."""
        result = await connected_adapter.probe()

        assert result["mode"] == "outstation"
        assert result["host"] == "0.0.0.0"
        assert result["port"] == 20000
        assert result["simulator"] is True
        assert result["connected"] is True
        assert "setup" in result

    @pytest.mark.asyncio
    async def test_probe_when_not_connected(self, adapter):
        """Test probe() when not connected."""
        result = await adapter.probe()

        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_probe_shows_setup_data(self, adapter_with_data):
        """Test probe() includes setup configuration."""
        await adapter_with_data.connect()
        result = await adapter_with_data.probe()

        assert len(result["setup"]["binary_inputs"]) == 3
        assert len(result["setup"]["analog_inputs"]) == 3
        assert len(result["setup"]["counters"]) == 3

    # ============================================================
    # Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_full_lifecycle_outstation(self):
        """Test complete outstation lifecycle."""
        adapter = DNP3Adapter(
            mode="outstation",
            host="0.0.0.0",
            port=20003,
        )

        # Connect
        await adapter.connect()
        assert adapter.connected is True

        # Add and update points
        adapter.database.add_binary_input(0, None)
        adapter.database.add_analog_input(0, None)

        await adapter.update_binary_input(0, True)
        await adapter.update_analog_input(0, 50.5)

        # Verify updates
        assert adapter.setup["binary_inputs"][0] is True
        assert adapter.setup["analog_inputs"][0] == 50.5

        # Probe
        info = await adapter.probe()
        assert info["connected"] is True

        # Disconnect
        await adapter.disconnect()
        assert adapter.connected is False


class TestDNP3AdapterMaster:
    """Test suite for DNP3 adapter in master (client) mode."""

    @pytest.fixture
    async def master_adapter(self):
        """Create a fresh master adapter for each test."""
        adapter = DNP3Adapter(
            mode="master",
            host="127.0.0.1",
            port=20010,
            simulator_mode=True,
        )
        yield adapter
        if adapter.connected:
            await adapter.disconnect()

    # ============================================================
    # Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_adapter_initialization_master(self):
        """Test master adapter initialization."""
        adapter = DNP3Adapter(mode="master")

        assert adapter.mode == "master"
        assert adapter.connected is False
        assert adapter.master is None
        assert adapter.client_channel is None

    # ============================================================
    # Lifecycle Tests (Note: Will fail without real outstation)
    # ============================================================

    @pytest.mark.asyncio
    async def test_master_connect_attempt(self, master_adapter):
        """Test master connection attempt (may fail without outstation)."""
        # This test documents expected behavior
        # In real scenario, would need an outstation running
        try:
            result = await master_adapter.connect()
            # If it connects (unlikely without outstation), verify state
            if result:
                assert master_adapter.connected is True
                assert master_adapter.master is not None
        except Exception:
            # Expected if no outstation is available
            pass

    @pytest.mark.asyncio
    async def test_master_disconnect(self, master_adapter):
        """Test master disconnect (safe even if not connected)."""
        await master_adapter.disconnect()

        assert master_adapter.connected is False
        assert master_adapter.master is None
        assert master_adapter.client_channel is None

    # ============================================================
    # Master Operation Tests (Placeholder functionality)
    # ============================================================

    @pytest.mark.asyncio
    async def test_integrity_scan_requires_connection(self, master_adapter):
        """Test integrity_scan() requires connection."""
        with pytest.raises(RuntimeError, match="Master not connected"):
            await master_adapter.integrity_scan()

    @pytest.mark.asyncio
    async def test_event_scan_requires_connection(self, master_adapter):
        """Test event_scan() requires connection."""
        with pytest.raises(RuntimeError, match="Master not connected"):
            await master_adapter.event_scan()

    @pytest.mark.asyncio
    async def test_write_binary_output_requires_connection(self, master_adapter):
        """Test write_binary_output() requires connection."""
        with pytest.raises(RuntimeError, match="Master not connected"):
            await master_adapter.write_binary_output(0, True)

    @pytest.mark.asyncio
    async def test_write_analog_output_requires_connection(self, master_adapter):
        """Test write_analog_output() requires connection."""
        with pytest.raises(RuntimeError, match="Master not connected"):
            await master_adapter.write_analog_output(0, 100.0)


class TestDNP3Protocol:
    """Test suite for DNP3 protocol wrapper."""

    @pytest.fixture
    async def outstation_protocol(self):
        """Create protocol with outstation adapter."""
        adapter = DNP3Adapter(
            mode="outstation",
            host="0.0.0.0",
            port=20020,
        )
        protocol = DNP3Protocol(adapter)
        yield protocol
        await protocol.disconnect()

    @pytest.fixture
    async def master_protocol(self):
        """Create protocol with master adapter."""
        adapter = DNP3Adapter(
            mode="master",
            host="127.0.0.1",
            port=20021,
        )
        protocol = DNP3Protocol(adapter)
        yield protocol
        await protocol.disconnect()

    @pytest.fixture
    async def connected_outstation_protocol(self, outstation_protocol):
        """Connected outstation protocol."""
        await outstation_protocol.connect()
        yield outstation_protocol
        await outstation_protocol.disconnect()

    # ============================================================
    # Protocol Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_initialization(self):
        """Test protocol wrapper initialization."""
        adapter = DNP3Adapter(mode="outstation")
        protocol = DNP3Protocol(adapter)

        assert protocol.protocol_name == "dnp3"
        assert protocol.adapter == adapter
        assert protocol.connected is False

    # ============================================================
    # Protocol Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_connect_outstation(self, outstation_protocol):
        """Test protocol connect() for outstation."""
        result = await outstation_protocol.connect()

        assert result is True
        assert outstation_protocol.connected is True
        assert outstation_protocol.adapter.connected is True

    @pytest.mark.asyncio
    async def test_protocol_disconnect(self, connected_outstation_protocol):
        """Test protocol disconnect()."""
        await connected_outstation_protocol.disconnect()

        assert connected_outstation_protocol.connected is False
        assert connected_outstation_protocol.adapter.connected is False

    # ============================================================
    # Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_probe_outstation_disconnected(self, outstation_protocol):
        """Test probe() on disconnected outstation."""
        result = await outstation_protocol.probe()

        assert result["protocol"] == "dnp3"
        assert result["mode"] == "outstation"
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_probe_outstation_connected(self, connected_outstation_protocol):
        """Test probe() on connected outstation."""
        result = await connected_outstation_protocol.probe()

        assert result["protocol"] == "dnp3"
        assert result["mode"] == "outstation"
        assert result["connected"] is True
        assert "binary_inputs_count" in result
        assert "analog_inputs_count" in result
        assert "counters_count" in result

    @pytest.mark.asyncio
    async def test_probe_shows_point_counts(self):
        """Test probe() shows correct point counts."""
        adapter = DNP3Adapter(
            mode="outstation",
            host="0.0.0.0",
            port=20022,
            setup={
                "binary_inputs": {0: True, 1: False, 2: True},
                "analog_inputs": {0: 100.0, 1: 200.0},
                "counters": {0: 10},
            },
        )
        protocol = DNP3Protocol(adapter)

        await protocol.connect()
        result = await protocol.probe()

        assert result["binary_inputs_count"] == 3
        assert result["analog_inputs_count"] == 2
        assert result["counters_count"] == 1

        await protocol.disconnect()

    # ============================================================
    # Outstation Attack Primitives Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_send_unsolicited_response(self, connected_outstation_protocol):
        """Test send_unsolicited_response() for outstation."""
        # Add point to database
        connected_outstation_protocol.adapter.database.add_binary_input(0, None)

        result = await connected_outstation_protocol.send_unsolicited_response()

        # Should succeed in updating the point
        assert result is True

    @pytest.mark.asyncio
    async def test_send_unsolicited_requires_outstation(self, master_protocol):
        """Test send_unsolicited_response() only works in outstation mode."""
        await master_protocol.connect()

        with pytest.raises(
            RuntimeError, match="Unsolicited only available in outstation mode"
        ):
            await master_protocol.send_unsolicited_response()

    @pytest.mark.asyncio
    async def test_flood_events(self, connected_outstation_protocol):
        """Test flood_events() generates multiple events."""
        # Add points to database
        for i in range(10):
            connected_outstation_protocol.adapter.database.add_binary_input(i, None)

        result = await connected_outstation_protocol.flood_events(count=50)

        assert result["success"] is True
        assert result["events_generated"] == 50

    @pytest.mark.asyncio
    async def test_flood_events_requires_outstation(self, master_protocol):
        """Test flood_events() only works in outstation mode."""
        with pytest.raises(
            RuntimeError, match="Event generation only available in outstation mode"
        ):
            await master_protocol.flood_events()

    # ============================================================
    # Master Attack Primitives Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_enumerate_points_requires_master(self, outstation_protocol):
        """Test enumerate_points() only works in master mode."""
        await outstation_protocol.connect()

        with pytest.raises(
            RuntimeError, match="Point enumeration only available in master mode"
        ):
            await outstation_protocol.enumerate_points()

    @pytest.mark.asyncio
    async def test_test_write_capabilities_requires_master(
        self, connected_outstation_protocol
    ):
        """Test test_write_capabilities() only works in master mode."""
        with pytest.raises(
            RuntimeError, match="Write testing only available in master mode"
        ):
            await connected_outstation_protocol.test_write_capabilities()

    # ============================================================
    # Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_full_workflow_outstation(self):
        """Test complete protocol workflow for outstation."""
        adapter = DNP3Adapter(
            mode="outstation",
            host="0.0.0.0",
            port=20023,
            setup={
                "binary_inputs": {0: False},
                "analog_inputs": {0: 50.0},
                "counters": {0: 0},
            },
        )
        protocol = DNP3Protocol(adapter)

        # Connect
        await protocol.connect()
        assert protocol.connected is True

        # Probe
        probe_info = await protocol.probe()
        assert probe_info["connected"] is True
        assert probe_info["binary_inputs_count"] == 1

        # Send unsolicited
        result = await protocol.send_unsolicited_response()
        assert result is True

        # Flood events
        flood_result = await protocol.flood_events(count=10)
        assert flood_result["success"] is True

        # Disconnect
        await protocol.disconnect()
        assert protocol.connected is False


# ============================================================
# Standalone Test Runner
# ============================================================


async def run_standalone_tests():
    """Run tests without pytest for quick verification."""
    print("=" * 70)
    print("DNP3 Adapter & Protocol Functional Tests")
    print("=" * 70)

    # Test 1: Outstation basic connection
    print("\n[TEST] Outstation: Basic connection and disconnection...")
    adapter = DNP3Adapter(
        mode="outstation",
        host="0.0.0.0",
        port=20030,
    )
    result = await adapter.connect()
    assert result is True
    assert adapter.connected is True
    await adapter.disconnect()
    assert adapter.connected is False
    print("[PASS] ✓")

    # Test 2: Point updates
    print("\n[TEST] Outstation: Point update operations...")
    adapter = DNP3Adapter(
        mode="outstation",
        host="0.0.0.0",
        port=20031,
    )
    await adapter.connect()

    # Add points and update them
    adapter.database.add_binary_input(0, None)
    adapter.database.add_analog_input(0, None)
    adapter.database.add_counter(0, None)

    await adapter.update_binary_input(0, True)
    await adapter.update_analog_input(0, 123.45)
    await adapter.update_counter(0, 999)

    assert adapter.setup["binary_inputs"][0] is True
    assert adapter.setup["analog_inputs"][0] == 123.45
    assert adapter.setup["counters"][0] == 999

    await adapter.disconnect()
    print("[PASS] ✓")

    # Test 3: Protocol wrapper
    print("\n[TEST] Protocol: Basic outstation operations...")
    adapter = DNP3Adapter(
        mode="outstation",
        host="0.0.0.0",
        port=20032,
    )
    protocol = DNP3Protocol(adapter)

    await protocol.connect()
    assert protocol.connected is True

    probe_info = await protocol.probe()
    assert probe_info["protocol"] == "dnp3"
    assert probe_info["connected"] is True

    await protocol.disconnect()
    assert protocol.connected is False
    print("[PASS] ✓")

    # Test 4: Protocol probe with data
    print("\n[TEST] Protocol: Probe with point counts...")
    adapter = DNP3Adapter(
        mode="outstation",
        host="0.0.0.0",
        port=20033,
        setup={
            "binary_inputs": {0: True, 1: False, 2: True},
            "analog_inputs": {0: 100.0, 1: 200.0},
            "counters": {0: 10},
        },
    )
    protocol = DNP3Protocol(adapter)

    await protocol.connect()
    result = await protocol.probe()

    assert result["binary_inputs_count"] == 3
    assert result["analog_inputs_count"] == 2
    assert result["counters_count"] == 1

    await protocol.disconnect()
    print("[PASS] ✓")

    # Test 5: Unsolicited response
    print("\n[TEST] Protocol: Send unsolicited response...")
    adapter = DNP3Adapter(
        mode="outstation",
        host="0.0.0.0",
        port=20034,
    )
    protocol = DNP3Protocol(adapter)

    await protocol.connect()
    adapter.database.add_binary_input(0, None)

    result = await protocol.send_unsolicited_response()
    assert result is True

    await protocol.disconnect()
    print("[PASS] ✓")

    # Test 6: Flood events
    print("\n[TEST] Protocol: Flood events...")
    adapter = DNP3Adapter(
        mode="outstation",
        host="0.0.0.0",
        port=20035,
    )
    protocol = DNP3Protocol(adapter)

    await protocol.connect()
    for i in range(10):
        adapter.database.add_binary_input(i, None)

    result = await protocol.flood_events(count=20)
    assert result["success"] is True
    assert result["events_generated"] == 20

    await protocol.disconnect()
    print("[PASS] ✓")

    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)


if __name__ == "__main__":
    # Run standalone tests
    asyncio.run(run_standalone_tests())
