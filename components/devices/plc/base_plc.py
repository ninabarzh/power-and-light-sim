# components/devices/plc/base_plc.py
"""Base class for all PLC devices."""

from abc import ABC

from components.devices.base_device import BaseDevice


class BasePLC(BaseDevice, ABC):
    """Abstract base class for all PLC devices."""

    protocol_name: str = "unknown"
    DEFAULT_SETUP: dict = {}

    def __init__(self, device_id: int, description: str = "", protocols=None):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )

    def get_memory_map(self) -> dict:
        """Return the current memory map/setup."""
        return self.setup

    def set_memory_value(self, memory_type: str, address: int, value):
        """Set a value in the device's memory map."""
        if memory_type in self.setup and address < len(self.setup[memory_type]):
            self.setup[memory_type][address] = value
            return True
        return False

    def get_memory_value(self, memory_type: str, address: int):
        """Get a value from the device's memory map."""
        if memory_type in self.setup and address < len(self.setup[memory_type]):
            return self.setup[memory_type][address]
        return None
