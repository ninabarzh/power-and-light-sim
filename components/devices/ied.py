# components/devices/ied.py
"""Intelligent Electronic Device (IED) for substations."""

from components.devices.base_device import BaseDevice


class IED(BaseDevice):
    """Intelligent Electronic Device using IEC 61850 (MMS, GOOSE, SV)."""

    protocol_name = "iec61850"

    DEFAULT_SETUP = {
        # IEC 61850 MMS data objects
        "logical_nodes": {},
        # GOOSE messages
        "goose_subscribers": [],
        "goose_publishers": [],
        # Sampled Values
        "sv_streams": [],
    }

    def __init__(self, device_id: int, description: str = "IED", protocols=None):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
