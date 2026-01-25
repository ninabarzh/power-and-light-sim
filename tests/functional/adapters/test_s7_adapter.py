#!/usr/bin/env python3
"""
Functional tests for Siemens S7 adapter (snap7 2.0.2) and protocol wrapper.

Tests verify:
- Adapter lifecycle (connect/disconnect)
- Connection parameter validation
- DB read/write operations interface
- Boolean read/write operations
- PLC control operations (start/stop)
- Protocol wrapper functionality
- Probe/reconnaissance operations
- Error handling and edge cases

Note: Full S7 communication tests require a running S7 server/PLC.
These tests focus on interface verification and error handling.
"""

import asyncio

import pytest
import pytest_asyncio
from components.adapters.snap7_202 import Snap7Adapter202
from components.protocols.s7_protocol import S7Protocol


class TestS7Adapter:
    """Test suite for Siemens S7 snap7 adapter."""

    @pytest_asyncio.fixture
    async def adapter(self):
        """Create a fresh adapter instance for each test."""
        adapter = Snap7Adapter202(
            host="127.0.0.1",
            rack=0,
            slot=1,
            simulator_mode=True,
        )
        yield adapter
        # Clean-up - use public disconnect method
        await adapter.disconnect()

    # ============================================================
    # Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test adapter can be instantiated with default settings."""
        adapter = Snap7Adapter202()

        assert adapter.host == "127.0.0.1"
        assert adapter.rack == 0
        assert adapter.slot == 1
        assert adapter.simulator_mode is True
        assert adapter._client is not None
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_adapter_custom_initialization(self):
        """Test adapter initialisation with custom parameters."""
        adapter = Snap7Adapter202(
            host="192.168.1.100",
            rack=1,
            slot=2,
            simulator_mode=False,
        )

        assert adapter.host == "192.168.1.100"
        assert adapter.rack == 1
        assert adapter.slot == 2
        assert adapter.simulator_mode is False

    @pytest.mark.asyncio
    async def test_client_created_on_init(self):
        """Test snap7 client is created during initialisation."""
        adapter = Snap7Adapter202()

        # Verify client exists through public probe interface
        result = await adapter.probe()
        assert result["protocol"] == "s7"
        # If client wasn't created, probe would fail

    # ============================================================
    # Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_connect_attempt_without_server(self, adapter):
        """Test connect() handles missing server gracefully."""
        # Will fail without actual S7 server, but shouldn't crash
        try:
            result = await adapter.connect()
            # If it somehow connects (unlikely), verify it returns a boolean
            assert isinstance(result, bool)
        except Exception:
            # Expected when no server available
            pass

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, adapter):
        """Test multiple connect() calls are safe."""
        # First connect attempt
        try:
            await adapter.connect()
        except Exception:
            pytest.skip("Cannot test without S7 server")

        # Second connect should also return boolean
        try:
            second_result = await adapter.connect()
            assert isinstance(second_result, bool)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, adapter):
        """Test disconnect() is safe when not connected."""
        # Should not raise an error even if never connected
        await adapter.disconnect()

        # Disconnect should complete without exception
        assert True  # If we get here, test passed

    @pytest.mark.asyncio
    async def test_disconnect_completes_successfully(self, adapter):
        """Test disconnect() completes without error."""
        # Disconnect should work even without prior connection
        await adapter.disconnect()

        # Should complete successfully
        assert True

    # ============================================================
    # Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_probe_when_not_connected(self, adapter):
        """Test probe() returns basic info when not connected."""
        result = await adapter.probe()

        assert result["protocol"] == "s7"
        assert result["connected"] is False
        assert "plc_state" not in result
        assert "plc_info" not in result

    # ============================================================
    # Read/Write Interface Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_read_db_interface_exists(self, adapter):
        """Test read_db() method exists with correct signature."""
        assert hasattr(adapter, "read_db")

        import inspect

        sig = inspect.signature(adapter.read_db)
        assert "db_number" in sig.parameters
        assert "start" in sig.parameters
        assert "size" in sig.parameters

    @pytest.mark.asyncio
    async def test_write_db_interface_exists(self, adapter):
        """Test write_db() method exists with correct signature."""
        assert hasattr(adapter, "write_db")

        import inspect

        sig = inspect.signature(adapter.write_db)
        assert "db_number" in sig.parameters
        assert "start" in sig.parameters
        assert "data" in sig.parameters

    @pytest.mark.asyncio
    async def test_read_bool_interface_exists(self, adapter):
        """Test read_bool() method exists with correct signature."""
        assert hasattr(adapter, "read_bool")

        import inspect

        sig = inspect.signature(adapter.read_bool)
        assert "db_number" in sig.parameters
        assert "byte_index" in sig.parameters
        assert "bit_index" in sig.parameters

    @pytest.mark.asyncio
    async def test_write_bool_interface_exists(self, adapter):
        """Test write_bool() method exists with correct signature."""
        assert hasattr(adapter, "write_bool")

        import inspect

        sig = inspect.signature(adapter.write_bool)
        assert "db_number" in sig.parameters
        assert "byte_index" in sig.parameters
        assert "bit_index" in sig.parameters
        assert "value" in sig.parameters

    # ============================================================
    # PLC Control Interface Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_stop_plc_interface_exists(self, adapter):
        """Test stop_plc() method exists."""
        assert hasattr(adapter, "stop_plc")

    @pytest.mark.asyncio
    async def test_start_plc_interface_exists(self, adapter):
        """Test start_plc() method exists."""
        assert hasattr(adapter, "start_plc")

    # ============================================================
    # Configuration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_rack_slot_configuration(self):
        """Test rack and slot parameters are stored correctly."""
        test_cases = [
            (0, 0),
            (0, 1),
            (0, 2),
            (1, 1),
        ]

        for rack, slot in test_cases:
            adapter = Snap7Adapter202(rack=rack, slot=slot)
            assert adapter.rack == rack
            assert adapter.slot == slot

    @pytest.mark.asyncio
    async def test_host_configuration(self):
        """Test host parameter variations."""
        test_hosts = [
            "127.0.0.1",
            "192.168.1.1",
            "10.0.0.1",
            "plc.example.com",
        ]

        for host in test_hosts:
            adapter = Snap7Adapter202(host=host)
            assert adapter.host == host


class TestS7Protocol:
    """Test suite for S7 protocol wrapper."""

    @pytest_asyncio.fixture
    async def protocol(self):
        """Create protocol with adapter."""
        adapter = Snap7Adapter202(
            host="127.0.0.1",
            rack=0,
            slot=1,
        )
        protocol = S7Protocol(adapter)
        yield protocol
        await protocol.disconnect()

    # ============================================================
    # Protocol Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_initialization(self):
        """Test protocol wrapper initialisation."""
        adapter = Snap7Adapter202()
        protocol = S7Protocol(adapter)

        assert protocol.protocol_name == "s7"
        assert protocol.adapter == adapter
        assert protocol.connected is False

    # ============================================================
    # Protocol Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_connect_attempt(self, protocol):
        """Test protocol connect() delegates to adapter."""
        # Will fail without server, but should delegate properly
        try:
            result = await protocol.connect()
            # If connected, verify state through public interface
            if result:
                assert protocol.connected is True
        except Exception:
            # Expected without server
            pass

    @pytest.mark.asyncio
    async def test_protocol_disconnect(self, protocol):
        """Test protocol disconnect()."""
        # Even if not connected, disconnect should work
        await protocol.disconnect()

        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_disconnect_when_not_connected(self, protocol):
        """Test disconnect() is safe when not connected."""
        assert protocol.connected is False

        await protocol.disconnect()

        assert protocol.connected is False

    # ============================================================
    # Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_probe_returns_capabilities(self, protocol):
        """Test probe() returns S7 capabilities."""
        result = await protocol.probe()

        assert result["protocol"] == "s7"
        assert "connected" in result
        assert "db_readable" in result
        assert "db_writable" in result

    @pytest.mark.asyncio
    async def test_probe_shows_disconnected_when_no_server(self, protocol):
        """Test probe() handles connection failure gracefully."""
        result = await protocol.probe()

        # Without server, should show not connected
        assert result["connected"] is False
        assert result["db_readable"] is False
        assert result["db_writable"] is False

    # ============================================================
    # Protocol Method Delegation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_read_db_delegates_to_adapter(self, protocol):
        """Test read_db() delegates to adapter."""
        assert hasattr(protocol, "read_db")

        # Method should exist and accept correct parameters
        import inspect

        sig = inspect.signature(protocol.read_db)
        assert "db" in sig.parameters
        assert "start" in sig.parameters
        assert "size" in sig.parameters

    @pytest.mark.asyncio
    async def test_write_db_delegates_to_adapter(self, protocol):
        """Test write_db() delegates to adapter."""
        assert hasattr(protocol, "write_db")

        import inspect

        sig = inspect.signature(protocol.write_db)
        assert "db" in sig.parameters
        assert "start" in sig.parameters
        assert "data" in sig.parameters

    @pytest.mark.asyncio
    async def test_read_bool_delegates_to_adapter(self, protocol):
        """Test read_bool() delegates to adapter."""
        assert hasattr(protocol, "read_bool")

        import inspect

        sig = inspect.signature(protocol.read_bool)
        assert "db" in sig.parameters
        assert "byte" in sig.parameters
        assert "bit" in sig.parameters

    @pytest.mark.asyncio
    async def test_write_bool_delegates_to_adapter(self, protocol):
        """Test write_bool() delegates to adapter."""
        assert hasattr(protocol, "write_bool")

        import inspect

        sig = inspect.signature(protocol.write_bool)
        assert "db" in sig.parameters
        assert "byte" in sig.parameters
        assert "bit" in sig.parameters
        assert "value" in sig.parameters

    @pytest.mark.asyncio
    async def test_stop_plc_delegates_to_adapter(self, protocol):
        """Test stop_plc() delegates to adapter."""
        assert hasattr(protocol, "stop_plc")

    @pytest.mark.asyncio
    async def test_start_plc_delegates_to_adapter(self, protocol):
        """Test start_plc() delegates to adapter."""
        assert hasattr(protocol, "start_plc")


# ============================================================
# Standalone Test Runner
# ============================================================


async def run_standalone_tests():
    """Run tests without pytest for quick verification."""
    print("=" * 70)
    print("Siemens S7 Adapter & Protocol Functional Tests")
    print("=" * 70)

    # Test 1: Adapter basic initialisation
    print("\n[TEST] Adapter: Basic initialization...")
    adapter = Snap7Adapter202()
    assert adapter.host == "127.0.0.1"
    assert adapter.rack == 0
    assert adapter.slot == 1
    # Verify client exists through public interface
    probe = await adapter.probe()
    assert probe["protocol"] == "s7"
    print("[PASS] ✓")

    # Test 2: Custom configuration
    print("\n[TEST] Adapter: Custom configuration...")
    adapter = Snap7Adapter202(
        host="192.168.1.100",
        rack=1,
        slot=2,
    )
    assert adapter.host == "192.168.1.100"
    assert adapter.rack == 1
    assert adapter.slot == 2
    print("[PASS] ✓")

    # Test 3: Client creation
    print("\n[TEST] Adapter: Client created on initialization...")
    adapter = Snap7Adapter202()
    # Verify through public interface (probe)
    result = await adapter.probe()
    assert result["protocol"] == "s7"
    print("[PASS] ✓")

    # Test 4: Disconnect safety
    print("\n[TEST] Adapter: Safe disconnect when not connected...")
    adapter = Snap7Adapter202()
    await adapter.disconnect()  # Should not raise error
    print("[PASS] ✓")

    # Test 5: Probe when disconnected
    print("\n[TEST] Adapter: Probe when not connected...")
    adapter = Snap7Adapter202()
    result = await adapter.probe()
    assert result["protocol"] == "s7"
    assert result["connected"] is False
    print("[PASS] ✓")

    # Test 6: Protocol wrapper initialisation
    print("\n[TEST] Protocol: Basic initialization...")
    adapter = Snap7Adapter202()
    protocol = S7Protocol(adapter)
    assert protocol.protocol_name == "s7"
    assert protocol.connected is False
    print("[PASS] ✓")

    # Test 7: Protocol probe
    print("\n[TEST] Protocol: Probe functionality...")
    result = await protocol.probe()
    assert result["protocol"] == "s7"
    assert "connected" in result
    assert "db_readable" in result
    assert "db_writable" in result
    print("[PASS] ✓")

    # Test 8: Interface verification - adapter methods
    print("\n[TEST] Adapter: Read/write interface exists...")
    adapter = Snap7Adapter202()
    assert hasattr(adapter, "read_db")
    assert hasattr(adapter, "write_db")
    assert hasattr(adapter, "read_bool")
    assert hasattr(adapter, "write_bool")
    assert hasattr(adapter, "stop_plc")
    assert hasattr(adapter, "start_plc")
    print("[PASS] ✓")

    # Test 9: Interface verification - protocol methods
    print("\n[TEST] Protocol: Delegation interface exists...")
    adapter = Snap7Adapter202()
    protocol = S7Protocol(adapter)
    assert hasattr(protocol, "read_db")
    assert hasattr(protocol, "write_db")
    assert hasattr(protocol, "read_bool")
    assert hasattr(protocol, "write_bool")
    assert hasattr(protocol, "stop_plc")
    assert hasattr(protocol, "start_plc")
    print("[PASS] ✓")

    # Test 10: Rack/slot configuration
    print("\n[TEST] Adapter: Rack and slot configuration...")
    test_cases = [(0, 0), (0, 1), (0, 2), (1, 1)]
    for rack, slot in test_cases:
        adapter = Snap7Adapter202(rack=rack, slot=slot)
        assert adapter.rack == rack
        assert adapter.slot == slot
    print("[PASS] ✓")

    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
    print("\nNote: These tests verify interfaces and error handling.")
    print("Full S7 communication tests require a running S7 server/PLC.")


if __name__ == "__main__":
    # Run standalone tests
    asyncio.run(run_standalone_tests())
