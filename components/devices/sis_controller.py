# components/devices/sis_controller.py
"""Safety Instrumented System (SIS) controller."""

from components.devices.base_device import BaseDevice


class SISController(BaseDevice):
    """Safety Instrumented System controller with Modbus and safety protocols."""

    protocol_name = "modbus"  # Primary protocol

    DEFAULT_SETUP = {
        # Modbus interface
        "coils": [False] * 32,
        "discrete_inputs": [False] * 32,
        "holding_registers": [0] * 32,
        "input_registers": [0] * 32,
        # Safety-specific data
        "safety_status": 0,
        "trip_conditions": [False] * 16,
    }

    def __init__(
        self, device_id: int, description: str = "SIS Controller", protocols=None
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )
