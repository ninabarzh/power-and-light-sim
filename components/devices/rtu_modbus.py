# components/devices/rtu_modbus.py
"""Modbus RTU device."""

from components.devices.base_device import BaseDevice


class RTUModbus(BaseDevice):
    """Remote Terminal Unit using Modbus TCP/RTU protocol."""

    protocol_name = "modbus"

    DEFAULT_SETUP = {
        "coils": [False] * 128,
        "discrete_inputs": [False] * 128,
        "holding_registers": [0] * 128,
        "input_registers": [0] * 128,
    }

    def __init__(self, device_id: int, description: str = "Modbus RTU", protocols=None):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
