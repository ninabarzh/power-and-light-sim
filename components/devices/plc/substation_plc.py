# components/devices/plc/substation_plc.py
"""Substation PLC - typically uses IEC 61850, GOOSE, and Modbus."""

from components.devices.plc.base_plc import BasePLC


class SubstationPLC(BasePLC):
    """Substation PLC with IEC 61850 and Modbus protocol support."""

    protocol_name = "iec61850"

    DEFAULT_SETUP = {
        # IEC 61850 MMS
        "logical_nodes": {},
        "goose_data": [],
        # Also support Modbus for local HMI/RTU
        "coils": [False] * 32,
        "discrete_inputs": [False] * 32,
        "holding_registers": [0] * 32,
        "input_registers": [0] * 32,
    }

    def __init__(
        self, device_id: int, description: str = "Substation PLC", protocols=None
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
