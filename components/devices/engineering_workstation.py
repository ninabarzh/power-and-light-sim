# components/devices/engineering_workstation.py
"""Engineering workstation for PLC programming and configuration."""

from components.devices.base_device import BaseDevice


class EngineeringWorkstation(BaseDevice):
    """Engineering workstation with S7, CIP, OPC UA, and file transfer support."""

    protocol_name = "s7"  # Example primary protocol

    DEFAULT_SETUP = {
        # Connected PLCs
        "plc_connections": {},
        # OPC UA client connections
        "opcua_connections": {},
        # File transfer capabilities
        "ftp_enabled": True,
        "tftp_enabled": True,
    }

    def __init__(
        self,
        device_id: int,
        description: str = "Engineering Workstation",
        protocols=None,
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
