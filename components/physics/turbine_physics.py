# components/physics/turbine_physics.py
"""
Steam turbine physics simulation.

Models turbine dynamics including:
- Shaft speed response to steam flow
- Temperature dynamics
- Vibration based on operating conditions
- Power output calculations
- Physical damage from overspeed
"""

import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class TurbineState:
    """Current turbine physical state."""

    shaft_speed_rpm: float = 0.0  # Current shaft speed
    steam_pressure_psi: float = 0.0  # Steam inlet pressure
    steam_temperature_f: float = 0.0  # Steam temperature
    bearing_temperature_f: float = 70.0  # Bearing temperature
    vibration_mils: float = 0.0  # Vibration amplitude
    power_output_mw: float = 0.0  # Electrical power output
    cumulative_overspeed_time: float = 0.0  # Time above rated speed
    damage_level: float = 0.0  # 0.0 = none, 1.0 = destroyed


@dataclass
class TurbineParameters:
    """Turbine design parameters."""

    rated_speed_rpm: int = 3600  # Rated operating speed
    rated_power_mw: float = 100.0  # Rated power output
    max_safe_speed_rpm: int = 3960  # 110% overspeed trip
    max_steam_pressure_psi: int = 2400  # Maximum steam pressure
    max_steam_temp_f: int = 1000  # Maximum steam temperature
    inertia: float = 5000.0  # Rotational inertia (kg·m²)
    acceleration_rate: float = 100.0  # RPM per second with full steam
    deceleration_rate: float = 50.0  # RPM per second natural decay
    vibration_normal_mils: float = 2.0  # Normal vibration level
    vibration_critical_mils: float = 10.0  # Dangerous vibration


class TurbinePhysics:
    """
    Simulates steam turbine physical behaviour.

    Updates turbine state based on control inputs (setpoints)
    and physical laws (thermodynamics, rotational dynamics).
    """

    def __init__(
        self,
        params: TurbineParameters | None = None,
        update_interval: float = 0.1,  # Physics update every 100ms
    ):
        self.params = params or TurbineParameters()
        self.state = TurbineState()
        self.update_interval = update_interval

        # Control inputs (set by PLC or operator)
        self.speed_setpoint_rpm: float = 0.0
        self.governor_enabled: bool = False
        self.emergency_trip: bool = False

        self._running = False
        self._update_task: asyncio.Task | None = None

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    async def start(self) -> None:
        """Start physics simulation loop."""
        if self._running:
            return

        self._running = True
        self._update_task = asyncio.create_task(self._physics_loop())

    async def stop(self) -> None:
        """Stop physics simulation."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None

    # ----------------------------------------------------------------
    # Physics simulation
    # ----------------------------------------------------------------

    async def _physics_loop(self) -> None:
        """Main physics update loop."""
        while self._running:
            await asyncio.sleep(self.update_interval)
            self._update_physics(self.update_interval)

    def _update_physics(self, dt: float) -> None:
        """
        Update turbine state based on physics.

        dt: time delta in seconds
        """
        # Emergency trip overrides everything
        if self.emergency_trip:
            self._emergency_shutdown(dt)
            return

        # Update shaft speed based on governor control
        if self.governor_enabled:
            self._update_shaft_speed(dt)
        else:
            # No governor - natural deceleration
            self._natural_deceleration(dt)

        # Update temperatures
        self._update_temperatures(dt)

        # Update vibration based on speed
        self._update_vibration()

        # Calculate power output
        self._update_power_output()

        # Track overspeed damage
        self._update_damage(dt)

    def _update_shaft_speed(self, dt: float) -> None:
        """Update shaft speed moving toward setpoint."""
        speed_error = self.speed_setpoint_rpm - self.state.shaft_speed_rpm

        if abs(speed_error) < 1.0:  # Close enough
            self.state.shaft_speed_rpm = self.speed_setpoint_rpm
            return

        # Acceleration proportional to error (simplified governor model)
        if speed_error > 0:
            # Accelerating - limited by steam flow rate
            accel = min(self.params.acceleration_rate, abs(speed_error) * 10)
            self.state.shaft_speed_rpm += accel * dt
        else:
            # Decelerating - governed braking
            decel = min(self.params.deceleration_rate, abs(speed_error) * 10)
            self.state.shaft_speed_rpm -= decel * dt

        # Physical limits
        self.state.shaft_speed_rpm = max(0.0, self.state.shaft_speed_rpm)

    def _natural_deceleration(self, dt: float) -> None:
        """Natural speed decay without governor."""
        if self.state.shaft_speed_rpm > 0:
            self.state.shaft_speed_rpm -= self.params.deceleration_rate * dt
            self.state.shaft_speed_rpm = max(0.0, self.state.shaft_speed_rpm)

    def _emergency_shutdown(self, dt: float) -> None:
        """Rapid shutdown on emergency trip."""
        # Fast deceleration (2x normal)
        if self.state.shaft_speed_rpm > 0:
            self.state.shaft_speed_rpm -= self.params.deceleration_rate * 2.0 * dt
            self.state.shaft_speed_rpm = max(0.0, self.state.shaft_speed_rpm)

        # Temperatures decay
        ambient = 70.0
        self.state.bearing_temperature_f += (
            (ambient - self.state.bearing_temperature_f) * 0.1 * dt
        )
        self.state.steam_temperature_f += (
            (ambient - self.state.steam_temperature_f) * 0.05 * dt
        )

    def _update_temperatures(self, dt: float) -> None:
        """Update temperature based on operating speed."""
        # Bearing temperature increases with speed and vibration
        speed_factor = self.state.shaft_speed_rpm / self.params.rated_speed_rpm
        vibration_factor = self.state.vibration_mils / self.params.vibration_normal_mils

        target_bearing_temp = 70.0 + (speed_factor * 80.0) + (vibration_factor * 20.0)

        # Temperature has thermal inertia
        temp_error = target_bearing_temp - self.state.bearing_temperature_f
        self.state.bearing_temperature_f += temp_error * 0.1 * dt

        # Steam temperature correlates with pressure/load
        # Simplified: high when running, decays when stopped
        if self.state.shaft_speed_rpm > 100:
            target_steam_temp = 600.0 + (speed_factor * 300.0)
        else:
            target_steam_temp = 70.0

        temp_error = target_steam_temp - self.state.steam_temperature_f
        self.state.steam_temperature_f += temp_error * 0.05 * dt

        # Steam pressure follows similar pattern
        if self.state.shaft_speed_rpm > 100:
            target_pressure = 1000.0 + (speed_factor * 800.0)
        else:
            target_pressure = 0.0

        pressure_error = target_pressure - self.state.steam_pressure_psi
        self.state.steam_pressure_psi += pressure_error * 0.1 * dt

    def _update_vibration(self) -> None:
        """Calculate vibration based on operating conditions."""
        # Vibration increases with speed deviation from rated
        speed_deviation = abs(self.state.shaft_speed_rpm - self.params.rated_speed_rpm)
        deviation_factor = speed_deviation / self.params.rated_speed_rpm

        # Normal vibration + deviation component
        self.state.vibration_mils = self.params.vibration_normal_mils * (
            1.0 + deviation_factor * 3.0
        )

        # Damage increases vibration
        self.state.vibration_mils *= 1.0 + self.state.damage_level

    def _update_power_output(self) -> None:
        """Calculate electrical power output."""
        # Power proportional to speed (simplified)
        speed_ratio = self.state.shaft_speed_rpm / self.params.rated_speed_rpm

        if speed_ratio < 0.2:  # Below minimum operating speed
            self.state.power_output_mw = 0.0
        else:
            # Power increases with speed, peaks near rated
            self.state.power_output_mw = self.params.rated_power_mw * min(
                speed_ratio, 1.1
            )

    def _update_damage(self, dt: float) -> None:
        """Track cumulative damage from overspeed."""
        if self.state.shaft_speed_rpm > self.params.rated_speed_rpm:
            # Track overspeed time
            self.state.cumulative_overspeed_time += dt

            # Damage accumulates faster at higher overspeeds
            overspeed_ratio = self.state.shaft_speed_rpm / self.params.rated_speed_rpm

            if overspeed_ratio > 1.1:  # Above 110% rated
                # Severe overspeed - rapid damage
                damage_rate = (overspeed_ratio - 1.1) * 0.01  # 1% per second at 120%
                self.state.damage_level += damage_rate * dt
                self.state.damage_level = min(1.0, self.state.damage_level)

    # ----------------------------------------------------------------
    # Control interface
    # ----------------------------------------------------------------

    def set_speed_setpoint(self, rpm: float) -> None:
        """Set target speed (called by PLC)."""
        self.speed_setpoint_rpm = max(0.0, rpm)

    def set_governor_enabled(self, enabled: bool) -> None:
        """Enable/disable governor control."""
        self.governor_enabled = enabled

    def trigger_emergency_trip(self) -> None:
        """Trigger emergency shutdown."""
        self.emergency_trip = True

    def reset_trip(self) -> None:
        """Reset emergency trip."""
        self.emergency_trip = False

    # ----------------------------------------------------------------
    # State access
    # ----------------------------------------------------------------

    def get_state(self) -> TurbineState:
        """Get current turbine state."""
        return self.state

    def get_telemetry(self) -> dict:
        """Get telemetry data suitable for PLC/SCADA."""
        return {
            "shaft_speed_rpm": int(self.state.shaft_speed_rpm),
            "power_output_mw": int(self.state.power_output_mw),
            "steam_pressure_psi": int(self.state.steam_pressure_psi),
            "steam_temperature_f": int(self.state.steam_temperature_f),
            "bearing_temperature_f": int(self.state.bearing_temperature_f),
            "vibration_mils": int(self.state.vibration_mils),
            "turbine_running": self.state.shaft_speed_rpm > 100,
            "trip_active": self.emergency_trip,
            "governor_online": self.governor_enabled,
            "overspeed_time_sec": int(self.state.cumulative_overspeed_time),
            "damage_percent": int(self.state.damage_level * 100),
        }
