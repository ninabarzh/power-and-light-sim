"""
Grid dynamics simulation.

Models:
- System frequency
- Voltage stability
- Load-generation balance
- Automatic frequency control and load shedding
- Grid trips for over/under-frequency or voltage violations
"""

import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class GridState:
    """Overall grid state."""

    frequency_hz: float = 50.0
    voltage_pu: float = 1.0
    total_load_mw: float = 0.0
    total_gen_mw: float = 0.0
    under_frequency_trip: bool = False
    over_frequency_trip: bool = False
    undervoltage_trip: bool = False
    overvoltage_trip: bool = False


@dataclass
class GridParameters:
    """Grid-wide control parameters."""

    nominal_frequency_hz: float = 50.0
    frequency_deadband_hz: float = 0.2
    max_frequency_hz: float = 51.0
    min_frequency_hz: float = 49.0
    voltage_deadband_pu: float = 0.05
    max_voltage_pu: float = 1.1
    min_voltage_pu: float = 0.9
    inertia_constant: float = 5000.0  # aggregate inertia (MW·s)
    damping: float = 1.0  # MW/Hz


class GridPhysics:
    """Simulates overall grid dynamics."""

    def __init__(
        self, params: GridParameters | None = None, update_interval: float = 0.1
    ):
        self.params = params or GridParameters()
        self.state = GridState()
        self.update_interval = update_interval
        self._running = False
        self._update_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._update_task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None

    async def _loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.update_interval)
            self._update_grid(self.update_interval)

    def _update_grid(self, dt: float) -> None:
        """Update frequency and voltage based on load-generation balance."""
        imbalance_mw = self.state.total_gen_mw - self.state.total_load_mw

        # Swing equation simplified
        df = (
            imbalance_mw
            - self.params.damping
            * (self.state.frequency_hz - self.params.nominal_frequency_hz)
        ) / self.params.inertia_constant
        self.state.frequency_hz += df * dt

        # Voltage deviation proportional to imbalance (very simplified)
        self.state.voltage_pu = 1.0 + imbalance_mw / 10000.0

        # Trips
        self.state.under_frequency_trip = (
            self.state.frequency_hz < self.params.min_frequency_hz
        )
        self.state.over_frequency_trip = (
            self.state.frequency_hz > self.params.max_frequency_hz
        )
        self.state.undervoltage_trip = (
            self.state.voltage_pu < self.params.min_voltage_pu
        )
        self.state.overvoltage_trip = self.state.voltage_pu > self.params.max_voltage_pu

    def get_state(self) -> GridState:
        return self.state

    def get_telemetry(self) -> dict:
        return {
            "frequency_hz": round(self.state.frequency_hz, 2),
            "voltage_pu": round(self.state.voltage_pu, 3),
            "under_frequency_trip": self.state.under_frequency_trip,
            "over_frequency_trip": self.state.over_frequency_trip,
            "undervoltage_trip": self.state.undervoltage_trip,
            "overvoltage_trip": self.state.overvoltage_trip,
        }
