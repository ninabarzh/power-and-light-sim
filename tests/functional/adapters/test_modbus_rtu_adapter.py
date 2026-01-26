#!/usr/bin/env python3
"""
Functional tests for Modbus RTU adapter (PyModbus 3.11.4) and protocol wrapper.
"""

import asyncio

import pytest

from components.adapters.modbus_rtu_adapter import ModbusRTUAdapter
from components.protocols.modbus_rtu_protocol import ModbusRTUProtocol


class TestModbusRTUAdapter:
    @pytest.fixture
    async def adapter(self):
        adapter = ModbusRTUAdapter(
            port="/dev/ttyUSB0",
            device_id=1,
            simulator_mode=False,
        )
        yield adapter
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        adapter = ModbusRTUAdapter(port="/dev/ttyUSB0", device_id=1)
        assert adapter.port == "/dev/ttyUSB0"
        assert adapter.device_id == 1
        assert adapter.baudrate == 9600
        assert adapter.simulator_mode is True
        assert adapter.client is None
        assert adapter.connected is False

    @pytest.mark.asyncio
    async def test_adapter_custom_initialization(self):
        custom_setup = {
            "coils": [True] * 32,
            "holding_registers": [1234] * 32,
        }
        adapter = ModbusRTUAdapter(
            port="/dev/ttyUSB1",
            device_id=5,
            baudrate=19200,
            simulator_mode=False,
            setup=custom_setup,
        )
        assert adapter.port == "/dev/ttyUSB1"
        assert adapter.device_id == 5
        assert adapter.baudrate == 19200
        assert adapter.setup == custom_setup

    @pytest.mark.asyncio
    async def test_adapter_connect_fails_without_serial_port(self, adapter):
        result = await adapter.connect()
        assert result is False
        assert adapter.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, adapter):
        await adapter.disconnect()
        assert adapter.connected is False

    @pytest.mark.asyncio
    async def test_read_without_connection(self, adapter):
        with pytest.raises(RuntimeError):
            await adapter.read_coils(0, 1)

    @pytest.mark.asyncio
    async def test_write_without_connection(self, adapter):
        with pytest.raises(RuntimeError):
            await adapter.write_coil(0, True)

    @pytest.mark.asyncio
    async def test_read_operations_interface(self, adapter):
        assert hasattr(adapter, "read_coils")
        assert hasattr(adapter, "read_holding_registers")

    @pytest.mark.asyncio
    async def test_write_operations_interface(self, adapter):
        assert hasattr(adapter, "write_coil")
        assert hasattr(adapter, "write_register")

    @pytest.mark.asyncio
    async def test_probe_when_not_connected(self, adapter):
        result = await adapter.probe()
        assert result["port"] == "/dev/ttyUSB0"
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_setup_stored_correctly(self):
        custom_setup = {
            "coils": [True] * 64,
            "holding_registers": [100] * 64,
        }
        adapter = ModbusRTUAdapter(
            port="/dev/ttyUSB0",
            device_id=1,
            setup=custom_setup,
        )
        assert adapter.setup == custom_setup


class TestModbusRTUProtocol:
    @pytest.fixture
    async def protocol(self):
        adapter = ModbusRTUAdapter(
            port="/dev/ttyUSB0",
            device_id=1,
            simulator_mode=False,
        )
        protocol = ModbusRTUProtocol(adapter)
        yield protocol
        await protocol.disconnect()

    @pytest.mark.asyncio
    async def test_protocol_initialization(self):
        adapter = ModbusRTUAdapter(port="/dev/ttyUSB0", device_id=1)
        protocol = ModbusRTUProtocol(adapter)
        assert protocol.protocol_name == "modbus_rtu"
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_connect_fails_without_serial_port(self, protocol):
        result = await protocol.connect()
        assert result is False
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_disconnect(self, protocol):
        await protocol.disconnect()
        assert protocol.connected is False

    @pytest.mark.asyncio
    async def test_protocol_operations_without_connect(self, protocol):
        """Test protocol operations when adapter is not connected."""
        # The protocol's scan_memory and test_write_access methods have try/except blocks
        # that catch exceptions and return empty/default results instead of re-raising
        result1 = await protocol.scan_memory(0, 10)
        result2 = await protocol.test_write_access(0)

        # They should return empty/default results, not raise exceptions
        assert isinstance(result1, dict)
        assert "coils" in result1
        assert "holding_registers" in result1

        assert isinstance(result2, dict)
        assert "coil_writable" in result2
        assert "register_writable" in result2

        # Both should indicate no access (since adapter is not connected)
        assert result2["coil_writable"] is False
        assert result2["register_writable"] is False

    @pytest.mark.asyncio
    async def test_probe_when_disconnected(self, protocol):
        result = await protocol.probe()
        assert result["protocol"] == "modbus_rtu"
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_protocol_interface_methods(self, protocol):
        assert hasattr(protocol, "scan_memory")
        assert hasattr(protocol, "test_write_access")
        assert hasattr(protocol, "probe")
        assert hasattr(protocol, "connect")
        assert hasattr(protocol, "disconnect")

        # Protocol should NOT have low-level adapter methods
        assert not hasattr(protocol, "read_coils")
        assert not hasattr(protocol, "write_coil")

    @pytest.mark.asyncio
    async def test_scan_memory_interface(self, protocol):
        import inspect

        assert hasattr(protocol, "scan_memory")
        sig = inspect.signature(protocol.scan_memory)
        params = list(sig.parameters.keys())
        assert "start" in params
        assert "count" in params

    @pytest.mark.asyncio
    async def test_test_write_access_interface(self, protocol):
        import inspect

        assert hasattr(protocol, "test_write_access")
        sig = inspect.signature(protocol.test_write_access)
        params = list(sig.parameters.keys())
        assert "address" in params


@pytest.mark.skip(reason="Requires actual serial port")
class TestModbusRTUAdapterSerialIntegration:
    @pytest.mark.asyncio
    async def test_serial_communication_with_real_port(self):
        pytest.skip("Requires actual serial port")


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
