#!/usr/bin/env python3
"""
Functional tests for IEC 61850 GOOSE adapter and protocol wrapper.

Tests verify:
- Adapter lifecycle (connect/disconnect)
- Interface configuration
- Subscription management
- Publishing interface
- Protocol wrapper functionality
- State tracking
- Error handling

Note: These are placeholder implementations. Tests focus on interface
verification and state management rather than actual GOOSE communication.
"""

import asyncio

import pytest
from components.adapters.iec61850_goose_adapter import IEC61850GOOSEAdapter
from components.protocols.iec61850_goose_protocol import IEC61850GOOSEProtocol


class TestIEC61850GOOSEAdapter:
    """Test suite for IEC 61850 GOOSE adapter."""

    @pytest.fixture
    async def adapter(self):
        """Create a fresh adapter instance for each test."""
        adapter = IEC61850GOOSEAdapter(
            interface="eth0",
            simulator_mode=True,
        )
        yield adapter
        # Cleanup
        await adapter.disconnect()

    @pytest.fixture
    async def connected_adapter(self, adapter):
        """Create and connect an adapter."""
        await adapter.connect()
        yield adapter
        await adapter.disconnect()

    # ============================================================
    # Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_adapter_initialization_default(self):
        """Test adapter can be instantiated with default settings."""
        adapter = IEC61850GOOSEAdapter()

        assert adapter.interface == "eth0"
        assert adapter.simulator_mode is True
        assert adapter.protocol_name == "iec61850_goose"
        assert adapter.connected is False
        assert adapter.subscriptions == []

    @pytest.mark.asyncio
    async def test_adapter_custom_initialization(self):
        """Test adapter initialisation with custom interface."""
        adapter = IEC61850GOOSEAdapter(
            interface="eth1",
            simulator_mode=False,
        )

        assert adapter.interface == "eth1"
        assert adapter.simulator_mode is False
        assert adapter.protocol_name == "iec61850_goose"

    # ============================================================
    # Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_connect_sets_connected_state(self, adapter):
        """Test connect() sets connected flag."""
        assert adapter.connected is False

        result = await adapter.connect()

        assert result is True
        assert adapter.connected is True

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, connected_adapter):
        """Test multiple connect() calls are safe."""
        assert connected_adapter.connected is True

        # Second connect should succeed
        result = await connected_adapter.connect()
        assert result is True
        assert connected_adapter.connected is True

    @pytest.mark.asyncio
    async def test_disconnect_clears_connected_state(self, connected_adapter):
        """Test disconnect() clears connected flag."""
        assert connected_adapter.connected is True

        await connected_adapter.disconnect()

        assert connected_adapter.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, adapter):
        """Test disconnect() is safe when not connected."""
        assert adapter.connected is False

        await adapter.disconnect()

        assert adapter.connected is False

    # ============================================================
    # Subscription Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_subscribe_goose_adds_subscription(self, adapter):
        """Test subscribe_goose() adds subscription to list."""
        goose_id = "GOOSE_CB1"

        await adapter.subscribe_goose(goose_id)

        assert goose_id in adapter.subscriptions
        assert len(adapter.subscriptions) == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_goose_ids(self, adapter):
        """Test subscribing to multiple GOOSE IDs."""
        goose_ids = ["GOOSE_CB1", "GOOSE_CB2", "GOOSE_CB3"]

        for goose_id in goose_ids:
            await adapter.subscribe_goose(goose_id)

        assert len(adapter.subscriptions) == 3
        for goose_id in goose_ids:
            assert goose_id in adapter.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_duplicate_goose_id(self, adapter):
        """Test subscribing to same GOOSE ID twice doesn't duplicate."""
        goose_id = "GOOSE_CB1"

        await adapter.subscribe_goose(goose_id)
        await adapter.subscribe_goose(goose_id)

        assert len(adapter.subscriptions) == 1
        assert adapter.subscriptions.count(goose_id) == 1

    @pytest.mark.asyncio
    async def test_subscriptions_persist_across_operations(self, adapter):
        """Test subscriptions are maintained."""
        await adapter.subscribe_goose("GOOSE_CB1")
        await adapter.subscribe_goose("GOOSE_CB2")

        # Subscriptions should persist
        assert len(adapter.subscriptions) == 2

        # Connect shouldn't affect subscriptions
        await adapter.connect()
        assert len(adapter.subscriptions) == 2

    # ============================================================
    # Publishing Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_publish_goose_interface_exists(self, adapter):
        """Test publish_goose() method exists."""
        assert hasattr(adapter, "publish_goose")

    @pytest.mark.asyncio
    async def test_publish_goose_returns_bool(self, adapter):
        """Test publish_goose() returns boolean."""
        result = await adapter.publish_goose("GOOSE_CB1", {"state": True})

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_publish_goose_placeholder_returns_false(self, adapter):
        """Test publish_goose() placeholder returns False."""
        # Placeholder implementation returns False
        result = await adapter.publish_goose("GOOSE_CB1", {"value": 100})

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_goose_accepts_various_data(self, adapter):
        """Test publish_goose() accepts different data types."""
        test_cases = [
            {"state": True},
            {"value": 100},
            {"status": "OK", "code": 42},
            {},
        ]

        for data in test_cases:
            result = await adapter.publish_goose("GOOSE_TEST", data)
            assert isinstance(result, bool)

    # ============================================================
    # Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_probe_when_not_connected(self, adapter):
        """Test probe() returns correct info when not connected."""
        result = await adapter.probe()

        assert result["protocol"] == "iec61850_goose"
        assert result["interface"] == "eth0"
        assert result["connected"] is False
        assert result["subscriptions"] == 0

    @pytest.mark.asyncio
    async def test_probe_when_connected(self, connected_adapter):
        """Test probe() returns correct info when connected."""
        result = await connected_adapter.probe()

        assert result["protocol"] == "iec61850_goose"
        assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_probe_shows_subscription_count(self, adapter):
        """Test probe() reflects subscription count."""
        await adapter.subscribe_goose("GOOSE_CB1")
        await adapter.subscribe_goose("GOOSE_CB2")

        result = await adapter.probe()

        assert result["subscriptions"] == 2

    @pytest.mark.asyncio
    async def test_probe_shows_interface(self):
        """Test probe() shows configured interface."""
        adapter = IEC61850GOOSEAdapter(interface="eth5")

        result = await adapter.probe()

        assert result["interface"] == "eth5"

    # ============================================================
    # Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete adapter lifecycle."""
        adapter = IEC61850GOOSEAdapter(interface="eth0")

        # Initial state
        assert adapter.connected is False
        assert len(adapter.subscriptions) == 0

        # Connect
        await adapter.connect()
        assert adapter.connected is True

        # Subscribe
        await adapter.subscribe_goose("GOOSE_CB1")
        await adapter.subscribe_goose("GOOSE_CB2")
        assert len(adapter.subscriptions) == 2

        # Probe
        probe_info = await adapter.probe()
        assert probe_info["connected"] is True
        assert probe_info["subscriptions"] == 2

        # Publish (placeholder)
        result = await adapter.publish_goose("GOOSE_CB1", {"state": True})
        assert isinstance(result, bool)

        # Disconnect
        await adapter.disconnect()
        assert adapter.connected is False


class TestIEC61850GOOSEProtocol:
    """Test suite for IEC 61850 GOOSE protocol wrapper."""

    @pytest.fixture
    async def protocol(self):
        """Create protocol with adapter."""
        adapter = IEC61850GOOSEAdapter(interface="eth0")
        protocol = IEC61850GOOSEProtocol(adapter)
        yield protocol
        await protocol.disconnect()

    @pytest.fixture
    async def connected_protocol(self, protocol):
        """Create and connect protocol."""
        await protocol.connect()
        yield protocol
        await protocol.disconnect()

    # ============================================================
    # Protocol Initialisation Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_initialization(self):
        """Test protocol wrapper initialisation."""
        adapter = IEC61850GOOSEAdapter()
        protocol = IEC61850GOOSEProtocol(adapter)

        assert protocol.protocol_name == "iec61850_goose"
        assert protocol.adapter == adapter

    # ============================================================
    # Protocol Lifecycle Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_connect(self, protocol):
        """Test protocol connect() delegates to adapter."""
        result = await protocol.connect()

        assert result is True
        assert protocol.adapter.connected is True

    @pytest.mark.asyncio
    async def test_protocol_disconnect(self, connected_protocol):
        """Test protocol disconnect() delegates to adapter."""
        await connected_protocol.disconnect()

        assert connected_protocol.adapter.connected is False

    # ============================================================
    # Protocol Probe Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_probe(self, protocol):
        """Test protocol probe() delegates to adapter."""
        result = await protocol.probe()

        assert result["protocol"] == "iec61850_goose"
        assert "interface" in result
        assert "connected" in result
        assert "subscriptions" in result

    # ============================================================
    # Protocol Subscription Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_subscribe_goose(self, protocol):
        """Test protocol subscribe_goose() delegates to adapter."""
        await protocol.subscribe_goose("GOOSE_CB1")

        assert "GOOSE_CB1" in protocol.adapter.subscriptions

    @pytest.mark.asyncio
    async def test_protocol_publish_goose(self, protocol):
        """Test protocol publish_goose() delegates to adapter."""
        result = await protocol.publish_goose("GOOSE_CB1", {"state": True})

        assert isinstance(result, bool)

    # ============================================================
    # Integration Tests
    # ============================================================

    @pytest.mark.asyncio
    async def test_protocol_full_workflow(self):
        """Test complete protocol workflow."""
        adapter = IEC61850GOOSEAdapter(interface="eth0")
        protocol = IEC61850GOOSEProtocol(adapter)

        # Connect
        await protocol.connect()
        assert adapter.connected is True

        # Subscribe
        await protocol.subscribe_goose("GOOSE_CB1")
        await protocol.subscribe_goose("GOOSE_CB2")

        # Probe
        probe_info = await protocol.probe()
        assert probe_info["subscriptions"] == 2

        # Publish
        result = await protocol.publish_goose("GOOSE_CB1", {"value": 42})
        assert isinstance(result, bool)

        # Disconnect
        await protocol.disconnect()
        assert adapter.connected is False


# ============================================================
# Standalone Test Runner
# ============================================================


async def run_standalone_tests():
    """Run tests without pytest for quick verification."""
    print("=" * 70)
    print("IEC 61850 GOOSE Adapter & Protocol Functional Tests")
    print("=" * 70)

    # Test 1: Adapter basic initialisation
    print("\n[TEST] Adapter: Basic initialization...")
    adapter = IEC61850GOOSEAdapter()
    assert adapter.interface == "eth0"
    assert adapter.protocol_name == "iec61850_goose"
    assert adapter.connected is False
    assert adapter.subscriptions == []
    print("[PASS] ✓")

    # Test 2: Custom interface
    print("\n[TEST] Adapter: Custom interface configuration...")
    adapter = IEC61850GOOSEAdapter(interface="eth5")
    assert adapter.interface == "eth5"
    print("[PASS] ✓")

    # Test 3: Connect/disconnect
    print("\n[TEST] Adapter: Connect and disconnect...")
    adapter = IEC61850GOOSEAdapter()
    result = await adapter.connect()
    assert result is True
    assert adapter.connected is True
    await adapter.disconnect()
    assert adapter.connected is False
    print("[PASS] ✓")

    # Test 4: Subscriptions
    print("\n[TEST] Adapter: GOOSE subscriptions...")
    adapter = IEC61850GOOSEAdapter()
    await adapter.subscribe_goose("GOOSE_CB1")
    await adapter.subscribe_goose("GOOSE_CB2")
    assert len(adapter.subscriptions) == 2
    assert "GOOSE_CB1" in adapter.subscriptions
    print("[PASS] ✓")

    # Test 5: Duplicate subscription
    print("\n[TEST] Adapter: Duplicate subscription handling...")
    adapter = IEC61850GOOSEAdapter()
    await adapter.subscribe_goose("GOOSE_CB1")
    await adapter.subscribe_goose("GOOSE_CB1")
    assert len(adapter.subscriptions) == 1
    print("[PASS] ✓")

    # Test 6: Publishing
    print("\n[TEST] Adapter: GOOSE publishing interface...")
    adapter = IEC61850GOOSEAdapter()
    result = await adapter.publish_goose("GOOSE_CB1", {"state": True})
    assert isinstance(result, bool)
    print("[PASS] ✓")

    # Test 7: Probe
    print("\n[TEST] Adapter: Probe functionality...")
    adapter = IEC61850GOOSEAdapter(interface="eth0")
    await adapter.connect()
    await adapter.subscribe_goose("GOOSE_CB1")

    probe_info = await adapter.probe()
    assert probe_info["protocol"] == "iec61850_goose"
    assert probe_info["interface"] == "eth0"
    assert probe_info["connected"] is True
    assert probe_info["subscriptions"] == 1
    print("[PASS] ✓")

    # Test 8: Protocol wrapper
    print("\n[TEST] Protocol: Basic operations...")
    adapter = IEC61850GOOSEAdapter()
    protocol = IEC61850GOOSEProtocol(adapter)

    assert protocol.protocol_name == "iec61850_goose"

    await protocol.connect()
    assert adapter.connected is True

    await protocol.subscribe_goose("GOOSE_CB1")
    assert "GOOSE_CB1" in adapter.subscriptions

    await protocol.disconnect()
    assert adapter.connected is False
    print("[PASS] ✓")

    # Test 9: Protocol probe
    print("\n[TEST] Protocol: Probe delegation...")
    adapter = IEC61850GOOSEAdapter()
    protocol = IEC61850GOOSEProtocol(adapter)

    result = await protocol.probe()
    assert result["protocol"] == "iec61850_goose"
    print("[PASS] ✓")

    # Test 10: Full workflow
    print("\n[TEST] Full workflow integration...")
    adapter = IEC61850GOOSEAdapter(interface="eth0")
    protocol = IEC61850GOOSEProtocol(adapter)

    await protocol.connect()
    await protocol.subscribe_goose("GOOSE_CB1")
    await protocol.subscribe_goose("GOOSE_CB2")

    probe_info = await protocol.probe()
    assert probe_info["subscriptions"] == 2

    result = await protocol.publish_goose("GOOSE_CB1", {"value": 100})
    assert isinstance(result, bool)

    await protocol.disconnect()
    print("[PASS] ✓")

    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
    print("\nNote: These tests verify the placeholder implementation.")
    print("Full GOOSE communication requires an actual IEC 61850 stack.")


if __name__ == "__main__":
    # Run standalone tests
    asyncio.run(run_standalone_tests())
