# components/devices/historian.py
"""Process historian / data archival system."""

from components.devices.base_device import BaseDevice


class Historian(BaseDevice):
    """Process historian with OPC UA, OPC DA, and Modbus support."""

    protocol_name = "opcua"

    DEFAULT_SETUP = {
        # OPC UA subscriptions
        "opcua_tags": {},
        # OPC DA tags (legacy)
        "opcda_tags": {},
        # Modbus polling targets
        "modbus_registers": {},
        # Time-series storage (simplified)
        "data_points": [],
    }

    def __init__(self, device_id: int, description: str = "Historian", protocols=None):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
