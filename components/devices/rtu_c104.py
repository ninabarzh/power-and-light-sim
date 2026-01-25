# components/devices/rtu_c104.py
"""IEC 60870-5-104 RTU device."""

from components.devices.base_device import BaseDevice


class RTUC104(BaseDevice):
    """Remote Terminal Unit using IEC 60870-5-104 protocol."""

    protocol_name = "iec104"

    DEFAULT_SETUP = {
        "single_points": [False] * 64,
        "double_points": [0] * 32,
        "measured_values": [0.0] * 64,
        "commands": [False] * 32,
    }

    def __init__(
        self, device_id: int, description: str = "IEC-104 RTU", protocols=None
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
