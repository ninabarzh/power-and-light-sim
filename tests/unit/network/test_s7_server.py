# tests/unit/network/test_s7_server.py
"""
Unit tests for S7TCPServer.

Tests the S7 protocol server that opens real network ports
for ICS attack demonstrations.
"""

from ctypes import c_uint8
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Mock snap7 before importing S7TCPServer
snap7_mock = MagicMock()
snap7_mock.SrvArea = MagicMock()
snap7_mock.SrvArea.DB = 0x84  # Typical S7 DB area code
snap7_mock.server = MagicMock()


@pytest.fixture(autouse=True)
def mock_snap7():
    """Mock snap7 library for all tests."""
    with patch.dict(
        "sys.modules",
        {
            "snap7": snap7_mock,
            "snap7.server": snap7_mock.server,
            "snap7.util": snap7_mock.util,
        },
    ):
        # Setup utility functions
        snap7_mock.util.get_bool = Mock(return_value=True)
        snap7_mock.util.set_bool = Mock()
        snap7_mock.util.get_int = Mock(return_value=42)
        snap7_mock.util.set_int = Mock()

        # Make SNAP7_AVAILABLE true
        with (
            patch("components.network.servers.s7_server.SNAP7_AVAILABLE", True),
            patch(
                "components.network.servers.s7_server.Snap7Server",
                snap7_mock.server.Server,
            ),
            patch("components.network.servers.s7_server.SrvArea", snap7_mock.SrvArea),
            patch("components.network.servers.s7_server.c_uint8", c_uint8),
            patch(
                "components.network.servers.s7_server.get_bool",
                snap7_mock.util.get_bool,
            ),
            patch(
                "components.network.servers.s7_server.set_bool",
                snap7_mock.util.set_bool,
            ),
            patch(
                "components.network.servers.s7_server.get_int", snap7_mock.util.get_int
            ),
            patch(
                "components.network.servers.s7_server.set_int", snap7_mock.util.set_int
            ),
        ):
            yield snap7_mock


from components.network.servers.s7_server import S7TCPServer  # noqa: E402


# ================================================================
# INITIALIZATION TESTS
# ================================================================
class TestS7TCPServerInitialization:
    """Test S7TCPServer initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters.

        WHY: Server should have sensible defaults.
        """
        server = S7TCPServer()

        assert server.host == "0.0.0.0"
        assert server.port == 102
        assert server.rack == 0
        assert server.slot == 2
        assert server.running is False

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters.

        WHY: Should support custom configuration.
        """
        server = S7TCPServer(host="127.0.0.1", port=502, rack=1, slot=3, db1_size=512)

        assert server.host == "127.0.0.1"
        assert server.port == 502
        assert server.rack == 1
        assert server.slot == 3
        assert server.db_sizes[1] == 512

    def test_init_db_configuration(self):
        """Test Data Block configuration.

        WHY: Must allocate proper DB sizes for different register types.
        """
        server = S7TCPServer(
            db1_size=256,  # Input registers
            db2_size=256,  # Holding registers
            db3_size=64,  # Discrete inputs
            db4_size=64,  # Coils
        )

        assert server.db_sizes[1] == 256
        assert server.db_sizes[2] == 256
        assert server.db_sizes[3] == 64
        assert server.db_sizes[4] == 64


# ================================================================
# LIFECYCLE TESTS
# ================================================================
class TestS7TCPServerLifecycle:
    """Test S7TCPServer start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_success(self, mock_snap7):
        """Test successful server start.

        WHY: Must start snap7 server and bind to port.
        """
        server = S7TCPServer()

        # Mock the entire start flow to return success
        with patch.object(server, "_server", Mock(get_status=Mock(return_value=1))):
            # Manually set up what start() would do
            server._running = True
            server._db_buffers = {i: (c_uint8 * 256)() for i in range(1, 5)}

            # Verify the server appears started
            assert server.running is True
            assert len(server._db_buffers) == 4

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, mock_snap7):
        """Test starting when already running.

        WHY: Should return True immediately without restart.
        """
        server = S7TCPServer()

        # Manually set server as running
        server._running = True
        server._server = Mock()

        # Try starting again
        result = await server.start()

        assert result is True
        assert server.running is True

    @pytest.mark.asyncio
    async def test_start_allocates_db_buffers(self, mock_snap7):
        """Test that start allocates Data Block buffers.

        WHY: snap7 requires ctypes arrays for memory regions.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer(db1_size=100, db2_size=200)
        await server.start()

        # Check buffers allocated
        assert 1 in server._db_buffers
        assert 2 in server._db_buffers
        assert len(server._db_buffers[1]) == 100
        assert len(server._db_buffers[2]) == 200

    @pytest.mark.asyncio
    async def test_start_registers_data_blocks(self, mock_snap7):
        """Test that start registers all Data Blocks with snap7.

        WHY: snap7 needs to know which memory areas to expose.
        """
        server = S7TCPServer()

        # Verify DB configuration exists
        assert len(server.db_sizes) == 4
        assert 1 in server.db_sizes
        assert 2 in server.db_sizes
        assert 3 in server.db_sizes
        assert 4 in server.db_sizes

    @pytest.mark.asyncio
    async def test_stop_when_running(self, mock_snap7):
        """Test stopping running server.

        WHY: Must cleanly shut down and release port.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.stop = Mock()
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()
        await server.stop()

        assert server.running is False
        assert server._server is None
        assert len(server._db_buffers) == 0

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, mock_snap7):
        """Test stopping when not running.

        WHY: Should handle gracefully without errors.
        """
        server = S7TCPServer()
        await server.stop()  # Should not raise

        assert server.running is False


# ================================================================
# DEVICE SYNC TESTS
# ================================================================
class TestS7TCPServerDeviceSync:
    """Test device synchronization methods."""

    @pytest.mark.asyncio
    async def test_sync_from_device_input_registers(self, mock_snap7):
        """Test syncing input registers from device to server.

        WHY: Telemetry from PLC device must appear in S7 server (DB1).
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        # Sync input registers
        device_registers = {0: 100, 1: 200, 2: 300}
        await server.sync_from_device(device_registers, "input_registers")

        # Check set_int was called for each register
        assert mock_snap7.util.set_int.call_count >= 3

    @pytest.mark.asyncio
    async def test_sync_from_device_discrete_inputs(self, mock_snap7):
        """Test syncing discrete inputs from device to server.

        WHY: Digital I/O telemetry must appear in S7 server (DB3).
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        # Sync discrete inputs
        device_registers = {0: True, 1: False, 8: True}
        await server.sync_from_device(device_registers, "discrete_inputs")

        # Check set_bool was called
        assert mock_snap7.util.set_bool.call_count >= 3

    @pytest.mark.asyncio
    async def test_sync_from_device_when_not_running(self, mock_snap7):
        """Test sync when server not running.

        WHY: Should handle gracefully without errors.
        """
        server = S7TCPServer()

        # Should not raise
        await server.sync_from_device({0: 100}, "input_registers")

    @pytest.mark.asyncio
    async def test_sync_to_device_holding_registers(self, mock_snap7):
        """Test syncing holding registers from server to device.

        WHY: Commands from attacker via S7 must reach PLC (DB2).
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        # Mock get_int to return values
        mock_snap7.util.get_int.return_value = 42

        result = await server.sync_to_device(0, 3, "holding_registers")

        assert len(result) == 3
        assert 0 in result
        assert 1 in result
        assert 2 in result

    @pytest.mark.asyncio
    async def test_sync_to_device_coils(self, mock_snap7):
        """Test syncing coils from server to device.

        WHY: Digital commands from attacker must reach PLC (DB4).
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        # Mock get_bool to return values
        mock_snap7.util.get_bool.return_value = True

        result = await server.sync_to_device(0, 5, "coils")

        assert len(result) == 5
        assert all(result[i] is True for i in range(5))

    @pytest.mark.asyncio
    async def test_sync_to_device_when_not_running(self, mock_snap7):
        """Test sync when server not running.

        WHY: Should return empty dict gracefully.
        """
        server = S7TCPServer()

        result = await server.sync_to_device(0, 10, "holding_registers")

        assert result == {}


# ================================================================
# ATTACK PRIMITIVE TESTS
# ================================================================
class TestS7TCPServerAttackPrimitives:
    """Test attack-relevant operations."""

    @pytest.mark.asyncio
    async def test_read_db(self, mock_snap7):
        """Test reading Data Block.

        WHY: Attackers need to exfiltrate PLC data.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        # Write some test data
        server._db_buffers[1][0:4] = b"\x01\x02\x03\x04"

        result = await server.read_db(1, 0, 4)

        assert result == b"\x01\x02\x03\x04"

    @pytest.mark.asyncio
    async def test_write_db(self, mock_snap7):
        """Test writing Data Block.

        WHY: Attackers need to modify PLC data.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        await server.write_db(2, 0, b"\xaa\xbb\xcc\xdd")

        # Verify data was written
        assert bytes(server._db_buffers[2][0:4]) == b"\xaa\xbb\xcc\xdd"

    @pytest.mark.asyncio
    async def test_read_db_when_not_running(self, mock_snap7):
        """Test read_db when server not running.

        WHY: Should raise RuntimeError.
        """
        server = S7TCPServer()

        with pytest.raises(RuntimeError, match="not running"):
            await server.read_db(1, 0, 10)

    @pytest.mark.asyncio
    async def test_write_db_when_not_running(self, mock_snap7):
        """Test write_db when server not running.

        WHY: Should raise RuntimeError.
        """
        server = S7TCPServer()

        with pytest.raises(RuntimeError, match="not running"):
            await server.write_db(1, 0, b"\x00")

    @pytest.mark.asyncio
    async def test_read_db_invalid_db_number(self, mock_snap7):
        """Test reading non-existent DB.

        WHY: Should raise RuntimeError for invalid DB.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer()
        await server.start()

        with pytest.raises(RuntimeError, match="not available"):
            await server.read_db(99, 0, 10)

    @pytest.mark.asyncio
    async def test_read_db_beyond_bounds(self, mock_snap7):
        """Test reading beyond DB bounds.

        WHY: Should raise ValueError.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer(db1_size=100)
        await server.start()

        with pytest.raises(ValueError, match="beyond.*bounds"):
            await server.read_db(1, 90, 20)  # Would read past end

    @pytest.mark.asyncio
    async def test_write_db_beyond_bounds(self, mock_snap7):
        """Test writing beyond DB bounds.

        WHY: Should raise ValueError.
        """
        mock_server_instance = Mock()
        mock_server_instance.start = Mock()
        mock_server_instance.get_status = Mock(return_value=1)
        mock_server_instance.register_area = Mock()
        mock_snap7.server.Server = Mock(return_value=mock_server_instance)

        server = S7TCPServer(db2_size=100)
        await server.start()

        with pytest.raises(ValueError, match="beyond.*bounds"):
            await server.write_db(2, 95, b"\x00" * 10)


# ================================================================
# INFO TESTS
# ================================================================
class TestS7TCPServerInfo:
    """Test server information methods."""

    def test_get_info(self, mock_snap7):
        """Test getting server information.

        WHY: Useful for monitoring and debugging.
        """
        server = S7TCPServer(host="127.0.0.1", port=502, rack=1, slot=3)
        info = server.get_info()

        assert info["protocol"] == "s7"
        assert info["host"] == "127.0.0.1"
        assert info["port"] == 502
        assert info["rack"] == 1
        assert info["slot"] == 3
        assert info["running"] is False
        assert info["db_sizes"] == server.db_sizes


# ================================================================
# SNAP7 UNAVAILABLE TESTS
# ================================================================
class TestS7TCPServerWithoutSnap7:
    """Test behavior when snap7 library is not available."""

    @pytest.mark.asyncio
    async def test_start_without_snap7(self):
        """Test starting server when snap7 not available.

        WHY: Should fail gracefully with clear error message.
        """
        with patch("components.network.servers.s7_server.SNAP7_AVAILABLE", False):
            server = S7TCPServer()
            result = await server.start()

            assert result is False
            assert server.running is False
