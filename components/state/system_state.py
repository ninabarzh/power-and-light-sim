# components/state/system_state.py
"""
Centralized state management for ICS simulation.

Tracks all devices, physics engines, and simulation state.
Provides unified interface for monitoring and control.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DeviceState:
    """State snapshot for a single device."""

    device_name: str
    device_type: str
    device_id: int
    protocols: list[str]
    online: bool = False
    memory_map: dict = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class SimulationState:
    """Overall simulation state."""

    started_at: datetime = field(default_factory=datetime.now)
    running: bool = False
    total_devices: int = 0
    devices_online: int = 0
    total_update_cycles: int = 0
    simulation_time: float = 0.0  # Simulated time in seconds


class SystemState:
    """
    Centralized state manager for ICS simulation.

    Maintains current state of all devices and physics engines.
    Provides snapshot and monitoring capabilities.
    """

    def __init__(self):
        self.devices: dict[str, DeviceState] = {}
        self.simulation = SimulationState()
        self._lock = asyncio.Lock()

    # ----------------------------------------------------------------
    # Device registration
    # ----------------------------------------------------------------

    async def register_device(
        self,
        device_name: str,
        device_type: str,
        device_id: int,
        protocols: list[str],
        metadata: dict = None,
    ) -> None:
        """Register a device with the state manager."""
        async with self._lock:
            self.devices[device_name] = DeviceState(
                device_name=device_name,
                device_type=device_type,
                device_id=device_id,
                protocols=protocols,
                online=False,
                metadata=metadata or {},
            )
            self.simulation.total_devices = len(self.devices)

    async def unregister_device(self, device_name: str) -> None:
        """Remove a device from state tracking."""
        async with self._lock:
            if device_name in self.devices:
                del self.devices[device_name]
                self.simulation.total_devices = len(self.devices)

    # ----------------------------------------------------------------
    # State updates
    # ----------------------------------------------------------------

    async def update_device(
        self,
        device_name: str,
        online: bool = None,
        memory_map: dict = None,
        metadata: dict = None,
    ) -> None:
        """Update device state."""
        async with self._lock:
            if device_name not in self.devices:
                return

            device = self.devices[device_name]

            if online is not None:
                device.online = online

            if memory_map is not None:
                device.memory_map = memory_map

            if metadata is not None:
                device.metadata.update(metadata)

            device.last_update = datetime.now()

            # Update counters
            self.simulation.devices_online = sum(
                1 for d in self.devices.values() if d.online
            )

    async def update_simulation_time(self, delta_seconds: float) -> None:
        """Update simulated time."""
        async with self._lock:
            self.simulation.simulation_time += delta_seconds
            self.simulation.total_update_cycles += 1

    # ----------------------------------------------------------------
    # State queries
    # ----------------------------------------------------------------

    async def get_device(self, device_name: str) -> DeviceState | None:
        """Get current state of a specific device."""
        async with self._lock:
            return self.devices.get(device_name)

    async def get_all_devices(self) -> dict[str, DeviceState]:
        """Get state of all devices."""
        async with self._lock:
            return self.devices.copy()

    async def get_devices_by_type(self, device_type: str) -> list[DeviceState]:
        """Get all devices of a specific type."""
        async with self._lock:
            return [d for d in self.devices.values() if d.device_type == device_type]

    async def get_devices_by_protocol(self, protocol: str) -> list[DeviceState]:
        """Get all devices supporting a specific protocol."""
        async with self._lock:
            return [d for d in self.devices.values() if protocol in d.protocols]

    async def get_simulation_state(self) -> SimulationState:
        """Get overall simulation state."""
        async with self._lock:
            return self.simulation

    # ----------------------------------------------------------------
    # Status reporting
    # ----------------------------------------------------------------

    async def get_summary(self) -> dict[str, Any]:
        """Get high-level summary of simulation state."""
        async with self._lock:
            return {
                "simulation": {
                    "running": self.simulation.running,
                    "started_at": self.simulation.started_at.isoformat(),
                    "uptime_seconds": (
                        datetime.now() - self.simulation.started_at
                    ).total_seconds(),
                    "simulation_time": self.simulation.simulation_time,
                    "update_cycles": self.simulation.total_update_cycles,
                },
                "devices": {
                    "total": self.simulation.total_devices,
                    "online": self.simulation.devices_online,
                    "offline": self.simulation.total_devices
                    - self.simulation.devices_online,
                },
                "device_types": self._count_device_types(),
                "protocols": self._count_protocols(),
            }

    def _count_device_types(self) -> dict[str, int]:
        """Count devices by type."""
        counts = {}
        for device in self.devices.values():
            counts[device.device_type] = counts.get(device.device_type, 0) + 1
        return counts

    def _count_protocols(self) -> dict[str, int]:
        """Count protocol usage across devices."""
        counts = {}
        for device in self.devices.values():
            for protocol in device.protocols:
                counts[protocol] = counts.get(protocol, 0) + 1
        return counts

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    async def mark_running(self, running: bool) -> None:
        """Mark simulation as running/stopped."""
        async with self._lock:
            self.simulation.running = running
            if running:
                self.simulation.started_at = datetime.now()

    async def reset(self) -> None:
        """Reset all state."""
        async with self._lock:
            self.devices.clear()
            self.simulation = SimulationState()
