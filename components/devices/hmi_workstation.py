# components/devices/hmi_workstation.py
"""Human-Machine Interface workstation."""

from components.devices.base_device import BaseDevice


class HMIWorkstation(BaseDevice):
    """HMI workstation with OPC UA and Modbus support."""

    protocol_name = "opcua"

    DEFAULT_SETUP = {
        # OPC UA client tags
        "opcua_tags": {},
        # Direct Modbus connections
        "modbus_connections": {},
        # HMI screens/tags
        "hmi_tags": {},
    }

    def __init__(
        self, device_id: int, description: str = "HMI Workstation", protocols=None
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
