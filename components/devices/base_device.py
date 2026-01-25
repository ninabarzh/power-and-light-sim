# components/devices/base_device.py
"""Abstract base for all simulated devices."""

import copy


class BaseDevice:
    """Abstract base for all simulated devices."""

    protocol_name: str = "unknown"
    DEFAULT_SETUP: dict = {}  # Override in subclasses if needed

    def __init__(self, device_id: int, description: str = "", protocols=None):
        self.device_id = device_id
        self.description = description
        self.protocols = (
            protocols or {}
        )  # Dict like {"modbus": adapter1, "opcua": adapter2}
        # Deep copy to prevent shared mutable state across instances
        self.setup = copy.deepcopy(self.DEFAULT_SETUP) if self.DEFAULT_SETUP else {}

    def info(self) -> str:
        return f"{self.__class__.__name__} (id={self.device_id}): {self.description}"

    def get_protocol(self, protocol_name: str):
        """Get a specific protocol adapter by name."""
        return self.protocols.get(protocol_name)

    def has_protocol(self, protocol_name: str) -> bool:
        """Check if device supports a specific protocol."""
        return protocol_name in self.protocols
