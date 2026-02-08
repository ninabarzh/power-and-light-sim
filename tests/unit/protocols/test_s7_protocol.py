# tests/unit/protocols/test_s7_protocol.py
"""
Unit tests for S7Protocol.

Tests the high-level S7 protocol wrapper that provides
attacker-relevant capabilities via an adapter pattern.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from components.protocols.s7.s7_protocol import S7Protocol


# ================================================================
# FIXTURES
# ================================================================
@pytest.fixture
def mock_adapter():
    """Create a mock S7 adapter."""
    adapter = Mock()
    adapter.connect = AsyncMock(return_value=True)
    adapter.disconnect = AsyncMock()
    adapter.read_db = AsyncMock()
    adapter.write_db = AsyncMock()
    adapter.read_bool = AsyncMock()
    adapter.write_bool = AsyncMock()
    adapter.stop_plc = AsyncMock()
    adapter.start_plc = AsyncMock()
    return adapter


@pytest.fixture
def s7_protocol(mock_adapter):
    """Create S7Protocol instance with mock adapter."""
    return S7Protocol(mock_adapter)


# ================================================================
# INITIALIZATION TESTS
# ================================================================
class TestS7ProtocolInitialization:
    """Test S7Protocol initialization."""

    def test_init_with_adapter(self, mock_adapter):
        """Test initialization with adapter.

        WHY: Must properly initialize with adapter dependency injection.
        """
        protocol = S7Protocol(mock_adapter)

        assert protocol.protocol_name == "s7"
        assert protocol.adapter == mock_adapter
        assert protocol.connected is False

    def test_inherits_from_base_protocol(self, s7_protocol):
        """Test that S7Protocol inherits from BaseProtocol.

        WHY: Ensures protocol follows the base protocol interface.
        """
        from components.protocols.base_protocol import BaseProtocol

        assert isinstance(s7_protocol, BaseProtocol)


# ================================================================
# LIFECYCLE TESTS
# ================================================================
class TestS7ProtocolLifecycle:
    """Test S7Protocol connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_success(self, s7_protocol, mock_adapter):
        """Test successful connection.

        WHY: Connection establishes communication with PLC.
        """
        mock_adapter.connect.return_value = True

        result = await s7_protocol.connect()

        assert result is True
        assert s7_protocol.connected is True
        mock_adapter.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, s7_protocol, mock_adapter):
        """Test failed connection.

        WHY: Must handle connection failures gracefully.
        """
        mock_adapter.connect.return_value = False

        result = await s7_protocol.connect()

        assert result is False
        assert s7_protocol.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self, s7_protocol, mock_adapter):
        """Test disconnection when connected.

        WHY: Clean disconnection releases resources.
        """
        # Connect first
        await s7_protocol.connect()
        assert s7_protocol.connected is True

        # Disconnect
        await s7_protocol.disconnect()

        assert s7_protocol.connected is False
        mock_adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, s7_protocol, mock_adapter):
        """Test disconnection when not connected.

        WHY: Should handle disconnect safely even if not connected.
        """
        assert s7_protocol.connected is False

        await s7_protocol.disconnect()

        assert s7_protocol.connected is False
        mock_adapter.disconnect.assert_not_awaited()


# ================================================================
# PROBE TESTS
# ================================================================
class TestS7ProtocolProbe:
    """Test S7Protocol probe functionality."""

    @pytest.mark.asyncio
    async def test_probe_when_not_connected(self, s7_protocol):
        """Test probe returns basic info when not connected.

        WHY: Reconnaissance should work even before connection.
        """
        result = await s7_protocol.probe()

        assert result["protocol"] == "s7"
        assert result["connected"] is False
        assert result["db_readable"] is False
        assert result["db_writable"] is False

    @pytest.mark.asyncio
    async def test_probe_db_readable(self, s7_protocol, mock_adapter):
        """Test probe detects readable Data Blocks.

        WHY: Identifies if DB read operations are possible.
        """
        # Setup: connect and mock successful DB read
        await s7_protocol.connect()
        mock_adapter.read_db.return_value = b"\x00"

        result = await s7_protocol.probe()

        assert result["protocol"] == "s7"
        assert result["connected"] is True
        assert result["db_readable"] is True
        mock_adapter.read_db.assert_awaited_once_with(1, 0, 1)

    @pytest.mark.asyncio
    async def test_probe_db_writable(self, s7_protocol, mock_adapter):
        """Test probe detects writable Data Blocks.

        WHY: Identifies if DB write operations are possible (attack surface).
        """
        # Setup: connect and mock successful DB read/write
        await s7_protocol.connect()
        mock_adapter.read_db.return_value = b"\x00"
        mock_adapter.write_db.return_value = None

        result = await s7_protocol.probe()

        assert result["protocol"] == "s7"
        assert result["connected"] is True
        assert result["db_readable"] is True
        assert result["db_writable"] is True
        mock_adapter.write_db.assert_awaited_once_with(1, 0, bytes([0x00]))

    @pytest.mark.asyncio
    async def test_probe_handles_read_error(self, s7_protocol, mock_adapter):
        """Test probe handles read errors gracefully.

        WHY: PLC might reject read attempts.
        """
        await s7_protocol.connect()
        mock_adapter.read_db.side_effect = Exception("Access denied")
        mock_adapter.write_db.side_effect = Exception("Access denied")

        result = await s7_protocol.probe()

        assert result["db_readable"] is False
        assert result["db_writable"] is False

    @pytest.mark.asyncio
    async def test_probe_handles_write_error(self, s7_protocol, mock_adapter):
        """Test probe handles write errors gracefully.

        WHY: PLC might be in read-only mode.
        """
        await s7_protocol.connect()
        mock_adapter.read_db.return_value = b"\x00"
        mock_adapter.write_db.side_effect = Exception("Write protected")

        result = await s7_protocol.probe()

        assert result["db_readable"] is True
        assert result["db_writable"] is False


# ================================================================
# DATA BLOCK OPERATION TESTS
# ================================================================
class TestS7ProtocolDataBlockOperations:
    """Test S7 Data Block read/write operations."""

    @pytest.mark.asyncio
    async def test_read_db(self, s7_protocol, mock_adapter):
        """Test reading from Data Block.

        WHY: Core operation for extracting PLC data.
        """
        mock_adapter.read_db.return_value = b"\x01\x02\x03\x04"

        result = await s7_protocol.read_db(1, 0, 4)

        assert result == b"\x01\x02\x03\x04"
        mock_adapter.read_db.assert_awaited_once_with(1, 0, 4)

    @pytest.mark.asyncio
    async def test_write_db(self, s7_protocol, mock_adapter):
        """Test writing to Data Block.

        WHY: Core operation for attacking PLC logic.
        """
        data = b"\x0a\x0b\x0c\x0d"

        await s7_protocol.write_db(2, 10, data)

        mock_adapter.write_db.assert_awaited_once_with(2, 10, data)

    @pytest.mark.asyncio
    async def test_read_bool(self, s7_protocol, mock_adapter):
        """Test reading boolean from Data Block.

        WHY: Digital I/O is often stored as bits.
        """
        mock_adapter.read_bool.return_value = True

        result = await s7_protocol.read_bool(3, 5, 2)

        assert result is True
        mock_adapter.read_bool.assert_awaited_once_with(3, 5, 2)

    @pytest.mark.asyncio
    async def test_write_bool(self, s7_protocol, mock_adapter):
        """Test writing boolean to Data Block.

        WHY: Flipping bits can trigger dangerous operations.
        """
        await s7_protocol.write_bool(4, 7, 3, True)

        mock_adapter.write_bool.assert_awaited_once_with(4, 7, 3, True)


# ================================================================
# PLC CONTROL TESTS
# ================================================================
class TestS7ProtocolPLCControl:
    """Test S7 PLC control operations."""

    @pytest.mark.asyncio
    async def test_stop_plc(self, s7_protocol, mock_adapter):
        """Test stopping PLC.

        WHY: Critical attack - can halt industrial processes.
        """
        await s7_protocol.stop_plc()

        mock_adapter.stop_plc.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_plc(self, s7_protocol, mock_adapter):
        """Test starting PLC.

        WHY: Can restart processes after attack or recovery.
        """
        await s7_protocol.start_plc()

        mock_adapter.start_plc.assert_awaited_once()


# ================================================================
# ERROR HANDLING TESTS
# ================================================================
class TestS7ProtocolErrorHandling:
    """Test S7Protocol error handling."""

    @pytest.mark.asyncio
    async def test_read_db_propagates_error(self, s7_protocol, mock_adapter):
        """Test read_db propagates adapter errors.

        WHY: Caller should handle connection/permission errors.
        """
        mock_adapter.read_db.side_effect = RuntimeError("Connection lost")

        with pytest.raises(RuntimeError, match="Connection lost"):
            await s7_protocol.read_db(1, 0, 10)

    @pytest.mark.asyncio
    async def test_write_db_propagates_error(self, s7_protocol, mock_adapter):
        """Test write_db propagates adapter errors.

        WHY: Caller should handle write protection errors.
        """
        mock_adapter.write_db.side_effect = PermissionError("Write protected")

        with pytest.raises(PermissionError, match="Write protected"):
            await s7_protocol.write_db(2, 0, b"\x00")

    @pytest.mark.asyncio
    async def test_stop_plc_propagates_error(self, s7_protocol, mock_adapter):
        """Test stop_plc propagates adapter errors.

        WHY: Stop command might fail if PLC in safety mode.
        """
        mock_adapter.stop_plc.side_effect = RuntimeError("Safety lock active")

        with pytest.raises(RuntimeError, match="Safety lock active"):
            await s7_protocol.stop_plc()


# ================================================================
# TYPE HINT VERIFICATION TESTS
# ================================================================
class TestS7ProtocolTypeHints:
    """Verify S7Protocol has proper type hints."""

    def test_connect_return_type(self):
        """Test connect has return type hint.

        WHY: Type safety and IDE support.
        """
        import inspect

        sig = inspect.signature(S7Protocol.connect)
        assert sig.return_annotation is bool

    def test_disconnect_return_type(self):
        """Test disconnect has return type hint.

        WHY: Type safety and IDE support.
        """
        import inspect

        sig = inspect.signature(S7Protocol.disconnect)
        assert sig.return_annotation is None

    def test_probe_return_type(self):
        """Test probe has return type hint.

        WHY: Type safety and IDE support.
        """
        import inspect

        sig = inspect.signature(S7Protocol.probe)
        assert sig.return_annotation == dict[str, object]

    def test_read_db_has_parameter_types(self):
        """Test read_db has parameter type hints.

        WHY: Type safety for DB operations.
        """
        import inspect

        sig = inspect.signature(S7Protocol.read_db)
        assert sig.parameters["db"].annotation is int
        assert sig.parameters["start"].annotation is int
        assert sig.parameters["size"].annotation is int
        assert sig.return_annotation is bytes

    def test_write_bool_has_parameter_types(self):
        """Test write_bool has parameter type hints.

        WHY: Type safety for boolean operations.
        """
        import inspect

        sig = inspect.signature(S7Protocol.write_bool)
        assert sig.parameters["db"].annotation is int
        assert sig.parameters["byte"].annotation is int
        assert sig.parameters["bit"].annotation is int
        assert sig.parameters["value"].annotation is bool
        assert sig.return_annotation is None
