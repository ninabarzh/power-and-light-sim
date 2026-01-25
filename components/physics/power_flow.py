"""
Electrical power flow simulation.

Models:
- Node voltages and phase angles
- Line currents and power flows
- Reactive power and losses
- Basic line overload detection
"""

import asyncio
from dataclasses import dataclass, field


@dataclass
class BusState:
    """State of a grid bus/node."""

    voltage_pu: float = 1.0  # Per-unit voltage
    angle_deg: float = 0.0  # Voltage phase angle
    load_mw: float = 0.0
    load_mvar: float = 0.0
    gen_mw: float = 0.0
    gen_mvar: float = 0.0


@dataclass
class LineState:
    """State of a transmission line."""

    from_bus: str = ""
    to_bus: str = ""
    current_a: float = 0.0
    mw_flow: float = 0.0
    mvar_flow: float = 0.0
    overload: bool = False


@dataclass
class GridParameters:
    """Electrical network parameters."""

    base_mva: float = 100.0
    line_max_mva: float = 150.0
    buses: dict[str, BusState] = field(default_factory=dict)
    lines: dict[str, LineState] = field(default_factory=dict)


class PowerFlow:
    """Simulates steady-state electrical power flow."""

    def __init__(
        self, params: GridParameters | None = None, update_interval: float = 0.1
    ):
        self.params = params or GridParameters()
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
            self._update_power_flow()

    def _update_power_flow(self) -> None:
        """Simplified DC/AC power flow update."""
        # Update line flows from bus injections
        for _line_id, line in self.params.lines.items():
            from_bus = self.params.buses[line.from_bus]
            to_bus = self.params.buses[line.to_bus]

            # Simple linear approximation: flow ~ voltage difference
            voltage_diff = from_bus.voltage_pu - to_bus.voltage_pu
            line.mw_flow = voltage_diff * 100.0  # simplified gain
            line.mvar_flow = 0.0  # ignoring reactive for now

            # Overload check
            apparent_mva = (line.mw_flow**2 + line.mvar_flow**2) ** 0.5
            line.overload = apparent_mva > self.params.line_max_mva

    # ----------------------------------------------------------------
    # Telemetry
    # ----------------------------------------------------------------
    def get_bus_states(self) -> dict[str, BusState]:
        return self.params.buses

    def get_line_states(self) -> dict[str, LineState]:
        return self.params.lines

    def get_telemetry(self) -> dict:
        """Aggregate telemetry for SCADA/PLC."""
        return {
            "buses": {
                k: {
                    "Vpu": round(v.voltage_pu, 3),
                    "angle_deg": round(v.angle_deg, 1),
                    "load_mw": round(v.load_mw, 1),
                    "gen_mw": round(v.gen_mw, 1),
                }
                for k, v in self.params.buses.items()
            },
            "lines": {
                k: {"mw_flow": round(v.mw_flow, 1), "overload": v.overload}
                for k, v in self.params.lines.items()
            },
        }
