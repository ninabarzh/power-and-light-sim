# tests/unit/protocols/test_opcua_protocol.py
"""
Unit tests for OPCUAProtocol.

Tests the high-level OPC UA protocol wrapper that provides
attacker-relevant capabilities via an adapter pattern.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from components.protocols.opcua.opcua_protocol import OPCUAProtocol


# ================================================================
# FIXTURES
# ================================================================
@pytest.fixture
def mock_adapter():
    """Create a mock OPC UA adapter."""
    adapter = Mock()
    adapter.connect = AsyncMock(return_value=True)
    adapter.disconnect = AsyncMock()
    adapter.browse_root = AsyncMock()
    adapter.read_node = AsyncMock()
    adapter.write_node = AsyncMock()
    return adapter


@pytest.fixture
def opcua_protocol(mock_adapter):
    """Create OPCUAProtocol instance with mock adapter."""
    return OPCUAProtocol(mock_adapter)


# ================================================================
# INITIALIZATION TESTS
# ================================================================
class TestOPCUAProtocolInitialization:
    """Test OPCUAProtocol initialization."""

    def test_init_with_adapter(self, mock_adapter):
        """Test initialization with adapter.

        WHY: Must properly initialize with adapter dependency injection.
        """
        protocol = OPCUAProtocol(mock_adapter)

        assert protocol.protocol_name == "opcua"
        assert protocol.adapter == mock_adapter
        assert protocol.connected is False

    def test_inherits_from_base_protocol(self, opcua_protocol):
        """Test that OPCUAProtocol inherits from BaseProtocol.

        WHY: Ensures protocol follows the base protocol interface.
        """
        from components.protocols.base_protocol import BaseProtocol

        assert isinstance(opcua_protocol, BaseProtocol)


# ================================================================
# LIFECYCLE TESTS
# ================================================================
class TestOPCUAProtocolLifecycle:
    """Test OPCUAProtocol connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_success(self, opcua_protocol, mock_adapter):
        """Test successful connection.

        WHY: Connection establishes communication with OPC UA server.
        """
        mock_adapter.connect.return_value = True

        result = await opcua_protocol.connect()

        assert result is True
        assert opcua_protocol.connected is True
        mock_adapter.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, opcua_protocol, mock_adapter):
        """Test failed connection.

        WHY: Must handle connection failures gracefully.
        """
        mock_adapter.connect.return_value = False

        result = await opcua_protocol.connect()

        assert result is False
        assert opcua_protocol.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self, opcua_protocol, mock_adapter):
        """Test disconnection when connected.

        WHY: Clean disconnection releases resources.
        """
        # Connect first
        await opcua_protocol.connect()
        assert opcua_protocol.connected is True

        # Disconnect
        await opcua_protocol.disconnect()

        assert opcua_protocol.connected is False
        mock_adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, opcua_protocol, mock_adapter):
        """Test disconnection when not connected.

        WHY: Should handle disconnect safely even if not connected.
        """
        assert opcua_protocol.connected is False

        await opcua_protocol.disconnect()

        assert opcua_protocol.connected is False
        mock_adapter.disconnect.assert_not_awaited()


# ================================================================
# PROBE TESTS
# ================================================================
class TestOPCUAProtocolProbe:
    """Test OPCUAProtocol probe functionality."""

    @pytest.mark.asyncio
    async def test_probe_connection_failed(self, opcua_protocol, mock_adapter):
        """Test probe when connection fails.

        WHY: Should return minimal info if can't connect.
        """
        mock_adapter.connect.return_value = False

        result = await opcua_protocol.probe()

        assert result["protocol"] == "opcua"
        assert result["connected"] is False
        assert result["browse"] is False
        assert result["read"] is False
        assert result["write"] is False

    @pytest.mark.asyncio
    async def test_probe_browse_success(self, opcua_protocol, mock_adapter):
        """Test probe detects browsing capability.

        WHY: Identifies if node enumeration is possible.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1", "ns=2;i=2"]

        result = await opcua_protocol.probe()

        assert result["connected"] is True
        assert result["browse"] is True
        mock_adapter.browse_root.assert_awaited_once()
        mock_adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_probe_browse_empty_list(self, opcua_protocol, mock_adapter):
        """Test probe when browse returns empty list.

        WHY: Empty node list means browse capability not available.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = []

        result = await opcua_protocol.probe()

        assert result["connected"] is True
        assert result["browse"] is False

    @pytest.mark.asyncio
    async def test_probe_read_success(self, opcua_protocol, mock_adapter):
        """Test probe detects read capability.

        WHY: Identifies if node values can be read (data exfiltration).
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1"]
        mock_adapter.read_node.return_value = 42

        result = await opcua_protocol.probe()

        assert result["connected"] is True
        assert result["browse"] is True
        assert result["read"] is True
        mock_adapter.read_node.assert_awaited_once_with("ns=2;i=1")

    @pytest.mark.asyncio
    async def test_probe_read_returns_none(self, opcua_protocol, mock_adapter):
        """Test probe when read returns None.

        WHY: None value means read capability not available.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1"]
        mock_adapter.read_node.return_value = None

        result = await opcua_protocol.probe()

        assert result["browse"] is True
        assert result["read"] is False

    @pytest.mark.asyncio
    async def test_probe_write_success(self, opcua_protocol, mock_adapter):
        """Test probe detects write capability.

        WHY: Identifies if node values can be written (attack surface).
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1"]
        mock_adapter.read_node.return_value = 42
        mock_adapter.write_node.return_value = True

        result = await opcua_protocol.probe()

        assert result["connected"] is True
        assert result["browse"] is True
        assert result["read"] is True
        assert result["write"] is True
        mock_adapter.write_node.assert_awaited_once_with("ns=2;i=1", 42)

    @pytest.mark.asyncio
    async def test_probe_write_failure(self, opcua_protocol, mock_adapter):
        """Test probe when write fails.

        WHY: Write might be denied by server security policy.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1"]
        mock_adapter.read_node.return_value = 42
        mock_adapter.write_node.return_value = False

        result = await opcua_protocol.probe()

        assert result["browse"] is True
        assert result["read"] is True
        assert result["write"] is False

    @pytest.mark.asyncio
    async def test_probe_handles_browse_error(self, opcua_protocol, mock_adapter):
        """Test probe handles browse errors gracefully.

        WHY: Server might reject browse requests.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.side_effect = Exception("Access denied")

        result = await opcua_protocol.probe()

        assert result["connected"] is True
        assert result["browse"] is False
        assert result["read"] is False
        assert result["write"] is False

    @pytest.mark.asyncio
    async def test_probe_handles_read_error(self, opcua_protocol, mock_adapter):
        """Test probe handles read errors gracefully.

        WHY: Server might reject read requests.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1"]
        mock_adapter.read_node.side_effect = Exception("Read denied")

        result = await opcua_protocol.probe()

        assert result["browse"] is True
        assert result["read"] is False
        assert result["write"] is False

    @pytest.mark.asyncio
    async def test_probe_handles_write_error(self, opcua_protocol, mock_adapter):
        """Test probe handles write errors gracefully.

        WHY: Server might reject write requests.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = ["ns=2;i=1"]
        mock_adapter.read_node.return_value = 42
        mock_adapter.write_node.side_effect = Exception("Write protected")

        result = await opcua_protocol.probe()

        assert result["browse"] is True
        assert result["read"] is True
        assert result["write"] is False

    @pytest.mark.asyncio
    async def test_probe_disconnects_after_completion(
        self, opcua_protocol, mock_adapter
    ):
        """Test probe disconnects after completion.

        WHY: Should clean up connection even if operations fail.
        """
        mock_adapter.connect.return_value = True
        mock_adapter.browse_root.return_value = []

        await opcua_protocol.probe()

        mock_adapter.disconnect.assert_awaited_once()


# ================================================================
# EXPLOITATION PRIMITIVE TESTS
# ================================================================
class TestOPCUAProtocolExploitation:
    """Test OPC UA exploitation primitives."""

    @pytest.mark.asyncio
    async def test_browse(self, opcua_protocol, mock_adapter):
        """Test browsing server nodes.

        WHY: Core reconnaissance operation for discovering attack targets.
        """
        mock_adapter.browse_root.return_value = [
            "ns=2;i=1",
            "ns=2;i=2",
            "ns=2;i=3",
        ]

        result = await opcua_protocol.browse()

        assert len(result) == 3
        assert "ns=2;i=1" in result
        mock_adapter.browse_root.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read(self, opcua_protocol, mock_adapter):
        """Test reading node value.

        WHY: Core operation for extracting process data.
        """
        mock_adapter.read_node.return_value = 42.5

        result = await opcua_protocol.read("ns=2;i=1")

        assert result == 42.5
        mock_adapter.read_node.assert_awaited_once_with("ns=2;i=1")

    @pytest.mark.asyncio
    async def test_write(self, opcua_protocol, mock_adapter):
        """Test writing node value.

        WHY: Core operation for attacking process control.
        """
        mock_adapter.write_node.return_value = True

        result = await opcua_protocol.write("ns=2;i=1", 100.0)

        assert result is True
        mock_adapter.write_node.assert_awaited_once_with("ns=2;i=1", 100.0)


# ================================================================
# ERROR HANDLING TESTS
# ================================================================
class TestOPCUAProtocolErrorHandling:
    """Test OPCUAProtocol error handling."""

    @pytest.mark.asyncio
    async def test_browse_propagates_error(self, opcua_protocol, mock_adapter):
        """Test browse propagates adapter errors.

        WHY: Caller should handle connection/permission errors.
        """
        mock_adapter.browse_root.side_effect = RuntimeError("Connection lost")

        with pytest.raises(RuntimeError, match="Connection lost"):
            await opcua_protocol.browse()

    @pytest.mark.asyncio
    async def test_read_propagates_error(self, opcua_protocol, mock_adapter):
        """Test read propagates adapter errors.

        WHY: Caller should handle node access errors.
        """
        mock_adapter.read_node.side_effect = PermissionError("Access denied")

        with pytest.raises(PermissionError, match="Access denied"):
            await opcua_protocol.read("ns=2;i=1")

    @pytest.mark.asyncio
    async def test_write_propagates_error(self, opcua_protocol, mock_adapter):
        """Test write propagates adapter errors.

        WHY: Caller should handle write protection errors.
        """
        mock_adapter.write_node.side_effect = RuntimeError("Write protected")

        with pytest.raises(RuntimeError, match="Write protected"):
            await opcua_protocol.write("ns=2;i=1", 0)


# ================================================================
# TYPE HINT VERIFICATION TESTS
# ================================================================
class TestOPCUAProtocolTypeHints:
    """Verify OPCUAProtocol has proper type hints."""

    def test_connect_return_type(self):
        """Test connect has return type hint.

        WHY: Type safety and IDE support.
        """
        import inspect

        sig = inspect.signature(OPCUAProtocol.connect)
        assert sig.return_annotation is bool

    def test_disconnect_return_type(self):
        """Test disconnect has return type hint.

        WHY: Type safety and IDE support.
        """
        import inspect

        sig = inspect.signature(OPCUAProtocol.disconnect)
        assert sig.return_annotation is None

    def test_probe_return_type(self):
        """Test probe has return type hint.

        WHY: Type safety and IDE support.
        """
        import inspect

        sig = inspect.signature(OPCUAProtocol.probe)
        assert sig.return_annotation == dict[str, object]
