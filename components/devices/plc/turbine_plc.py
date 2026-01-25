# components/devices/plc/turbine_plc.py
"""Steam Turbine PLC - typically uses Modbus and OPC UA."""

from components.devices.plc.base_plc import BasePLC


class TurbinePLC(BasePLC):
    """Steam turbine PLC with Modbus and OPC UA protocol support."""

    protocol_name = "modbus"

    DEFAULT_SETUP = {
        "coils": [False] * 16,
        "discrete_inputs": [False] * 16,
        "holding_registers": [0] * 16,
        "input_registers": [0] * 16,
    }

    def __init__(
        self, device_id: int, description: str = "Steam turbine PLC", protocols=None
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )

    # Convenience methods for common steam turbine operations
    def get_shaft_speed(self) -> int:
        """Get shaft speed in RPM from input register 0."""
        return self.setup["input_registers"][0]

    def get_power_output(self) -> int:
        """Get power output in MW from input register 1."""
        return self.setup["input_registers"][1]

    def get_steam_pressure(self) -> int:
        """Get steam pressure in PSI from input register 2."""
        return self.setup["input_registers"][2]

    def get_steam_temperature(self) -> int:
        """Get steam temperature in °F from input register 3."""
        return self.setup["input_registers"][3]

    def get_vibration_level(self) -> int:
        """Get vibration level in mils from input register 4."""
        return self.setup["input_registers"][4]

    def is_turbine_running(self) -> bool:
        """Check if turbine is running (discrete input 0)."""
        return self.setup["discrete_inputs"][0]

    def is_trip_active(self) -> bool:
        """Check if emergency trip is active (discrete input 1)."""
        return self.setup["discrete_inputs"][1]

    def is_governor_online(self) -> bool:
        """Check if governor control is online (discrete input 2)."""
        return self.setup["discrete_inputs"][2]

    def set_turbine_enable(self, enable: bool) -> None:
        """Enable/disable turbine (coil 0)."""
        self.setup["coils"][0] = enable

    def set_governor_control(self, enable: bool) -> None:
        """Enable/disable governor control (coil 1)."""
        self.setup["coils"][1] = enable

    def emergency_trip(self) -> None:
        """Trigger emergency trip (coil 2)."""
        self.setup["coils"][2] = True
