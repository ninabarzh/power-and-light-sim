# components/devices/scada_server_enhanced.py
"""
Enhanced SCADA Server with multi-protocol support.

Functions:
- Polls field devices (PLCs, RTUs) for telemetry
- Aggregates data from multiple protocols
- Maintains historian data
- Alarm management
- Operator interface via OPC UA/Modbus

Protocols: Modbus (master), OPC UA (server), IEC-104 (master)
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from components.devices.base_device import BaseDevice


@dataclass
class AlarmDefinition:
    """Alarm configuration."""

    tag_name: str
    high_limit: float
    low_limit: float
    priority: int = 1  # 1=critical, 2=high, 3=medium, 4=low
    enabled: bool = True


@dataclass
class AlarmEvent:
    """Active or historical alarm."""

    timestamp: datetime
    tag_name: str
    value: float
    limit: float
    alarm_type: str  # "HIGH" or "LOW"
    priority: int
    acknowledged: bool = False


@dataclass
class TagValue:
    """Current tag value with metadata."""

    name: str
    value: float
    timestamp: datetime
    quality: str = "GOOD"  # GOOD, BAD, UNCERTAIN
    source_device: str = ""


class SCADAServerEnhanced(BaseDevice):
    """
    Enhanced SCADA server with polling, historian, and alarm management.

    Memory map (Modbus interface for operators/HMI):
      Holding Registers:
        5000-5099: Tag values (scaled, read-only via Modbus)
        5100: Active alarm count
        5101: Unacknowledged alarm count

      Input Registers:
        6000-6099: Current tag values (live data)
        6100-6199: Tag quality codes (0=GOOD, 1=BAD, 2=UNCERTAIN)

      Coils:
        200-299: Alarm acknowledge flags

      Discrete Inputs:
        200-299: Alarm active flags
    """

    protocol_name = "opcua"  # Primary protocol

    DEFAULT_SETUP = {
        "coils": [False] * 512,
        "discrete_inputs": [False] * 512,
        "holding_registers": [0] * 8192,
        "input_registers": [0] * 8192,
    }

    def __init__(
        self,
        device_id: int,
        description: str = "SCADA Server",
        protocols=None,
        poll_interval: float = 1.0,  # Poll devices every 1 second
        historian_size: int = 10000,
    ):
        super().__init__(
            device_id=device_id, description=description, protocols=protocols
        )

        self.poll_interval = poll_interval
        self.historian_size = historian_size

        # Data storage
        self.tags: dict[str, TagValue] = {}  # Current values
        self.historian: deque = deque(maxlen=historian_size)  # Historical data
        self.alarms: dict[str, AlarmDefinition] = {}  # Alarm configs
        self.active_alarms: list[AlarmEvent] = []  # Current alarms
        self.alarm_history: deque = deque(maxlen=1000)  # Historical alarms

        # Device polling configuration
        self.polled_devices: dict[str, dict] = {}  # device_name -> config

        # Task management
        self._running = False
        self._poll_task: asyncio.Task | None = None
        self._alarm_task: asyncio.Task | None = None

        # Initialize default alarms
        self._initialize_alarms()

    def _initialize_alarms(self) -> None:
        """Set up default alarm definitions."""
        # Turbine alarms
        self.alarms["turbine_speed_high"] = AlarmDefinition(
            tag_name="turbine_1.speed",
            high_limit=3700,  # Above rated speed
            low_limit=0,
            priority=1,
        )

        self.alarms["turbine_temp_high"] = AlarmDefinition(
            tag_name="turbine_1.bearing_temp",
            high_limit=250,  # Bearing temperature alarm
            low_limit=0,
            priority=1,
        )

        self.alarms["turbine_vibration_high"] = AlarmDefinition(
            tag_name="turbine_1.vibration",
            high_limit=8,  # Elevated vibration
            low_limit=0,
            priority=2,
        )

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    async def start(self) -> None:
        """Start SCADA polling and alarm monitoring."""
        if self._running:
            return

        self._running = True
        self._poll_task = asyncio.create_task(self._polling_loop())
        self._alarm_task = asyncio.create_task(self._alarm_loop())

    async def stop(self) -> None:
        """Stop SCADA operations."""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._alarm_task:
            self._alarm_task.cancel()
            try:
                await self._alarm_task
            except asyncio.CancelledError:
                pass

    # ----------------------------------------------------------------
    # Device registration
    # ----------------------------------------------------------------

    def register_device(
        self, device_name: str, protocol: str, tags: dict[str, int]
    ) -> None:
        """
        Register a device for polling.

        Args:
            device_name: Name of device
            protocol: Protocol to use (modbus, opcua, etc.)
            tags: Dict mapping tag_name -> address
                  e.g., {"speed": 2000, "power": 2001}
        """
        self.polled_devices[device_name] = {
            "protocol": protocol,
            "tags": tags,
            "last_poll": None,
        }

    # ----------------------------------------------------------------
    # Polling loop
    # ----------------------------------------------------------------

    async def _polling_loop(self) -> None:
        """Main polling loop - queries field devices."""
        while self._running:
            await asyncio.sleep(self.poll_interval)

            for device_name, config in self.polled_devices.items():
                await self._poll_device(device_name, config)

            # Update memory map for Modbus/OPC UA access
            self._update_memory_map()

    async def _poll_device(self, device_name: str, config: dict) -> None:
        """Poll a single device for its configured tags."""
        protocol_name = config["protocol"]
        tags = config["tags"]

        # Get protocol adapter from our protocols dict
        protocol = self.protocols.get(protocol_name)
        if not protocol:
            return

        # Ensure connected
        if not protocol.connected:
            try:
                await protocol.connect()
            except Exception:
                return

        # Read each tag
        for tag_name, address in tags.items():
            try:
                full_tag_name = f"{device_name}.{tag_name}"

                # Read based on protocol
                if protocol_name == "modbus":
                    # Read input register
                    result = await protocol.adapter.read_input_registers(address, 1)
                    if not result.isError():
                        value = float(result.registers[0])
                        self._update_tag(full_tag_name, value, device_name)

                # Add other protocols as needed (OPC UA, IEC-104, etc.)

            except Exception:
                # Mark tag as bad quality
                full_tag_name = f"{device_name}.{tag_name}"
                if full_tag_name in self.tags:
                    self.tags[full_tag_name].quality = "BAD"

        config["last_poll"] = datetime.now()

    def _update_tag(self, tag_name: str, value: float, source: str) -> None:
        """Update tag value and add to historian."""
        tag_value = TagValue(
            name=tag_name,
            value=value,
            timestamp=datetime.now(),
            quality="GOOD",
            source_device=source,
        )

        self.tags[tag_name] = tag_value

        # Add to historian
        self.historian.append(
            {
                "tag": tag_name,
                "value": value,
                "timestamp": tag_value.timestamp.isoformat(),
                "quality": tag_value.quality,
            }
        )

    # ----------------------------------------------------------------
    # Alarm monitoring
    # ----------------------------------------------------------------

    async def _alarm_loop(self) -> None:
        """Monitor tags for alarm conditions."""
        while self._running:
            await asyncio.sleep(0.5)  # Check alarms every 500ms

            for alarm_name, alarm_def in self.alarms.items():
                if not alarm_def.enabled:
                    continue

                # Get current tag value
                tag = self.tags.get(alarm_def.tag_name)
                if not tag or tag.quality != "GOOD":
                    continue

                # Check limits
                alarm_active = False
                alarm_type: str | None = None

                if tag.value > alarm_def.high_limit:
                    alarm_active = True
                    alarm_type = "HIGH"
                elif tag.value < alarm_def.low_limit:
                    alarm_active = True
                    alarm_type = "LOW"

                # Manage alarm state
                existing_alarm = self._find_active_alarm(alarm_name)

                if alarm_active and not existing_alarm and alarm_type is not None:
                    # New alarm
                    alarm_event = AlarmEvent(
                        timestamp=datetime.now(),
                        tag_name=alarm_def.tag_name,
                        value=tag.value,
                        limit=(
                            alarm_def.high_limit
                            if alarm_type == "HIGH"
                            else alarm_def.low_limit
                        ),
                        alarm_type=alarm_type,
                        priority=alarm_def.priority,
                    )
                    self.active_alarms.append(alarm_event)
                    self.alarm_history.append(alarm_event)

                elif not alarm_active and existing_alarm:
                    # Alarm cleared
                    self.active_alarms.remove(existing_alarm)

            # Update alarm counts in memory
            self._update_alarm_memory()

    def _find_active_alarm(self, alarm_name: str) -> AlarmEvent | None:
        """Find active alarm by name."""
        alarm_def = self.alarms.get(alarm_name)
        if not alarm_def:
            return None

        for alarm in self.active_alarms:
            if alarm.tag_name == alarm_def.tag_name:
                return alarm
        return None

    # ----------------------------------------------------------------
    # Memory map updates
    # ----------------------------------------------------------------

    def _update_memory_map(self) -> None:
        """Update Modbus/OPC UA memory map with current tag values."""
        # Map first 100 tags to registers 6000-6099
        tag_names = sorted(self.tags.keys())[:100]

        for idx, tag_name in enumerate(tag_names):
            tag = self.tags[tag_name]

            # Input register - current value (scaled to int)
            self.setup["input_registers"][6000 + idx] = int(tag.value)

            # Quality code
            quality_code = {"GOOD": 0, "BAD": 1, "UNCERTAIN": 2}.get(tag.quality, 1)
            self.setup["input_registers"][6100 + idx] = quality_code

            # Also in holding registers for compatibility
            self.setup["holding_registers"][5000 + idx] = int(tag.value)

    def _update_alarm_memory(self) -> None:
        """Update alarm status in memory map."""
        # Alarm counts
        self.setup["holding_registers"][5100] = len(self.active_alarms)
        self.setup["holding_registers"][5101] = sum(
            1 for a in self.active_alarms if not a.acknowledged
        )

        # Alarm flags in discrete inputs
        for idx, _alarm in enumerate(self.active_alarms[:100]):
            self.setup["discrete_inputs"][200 + idx] = True

    # ----------------------------------------------------------------
    # Operator interface
    # ----------------------------------------------------------------

    def acknowledge_alarm(self, alarm_index: int) -> bool:
        """Acknowledge an active alarm."""
        if 0 <= alarm_index < len(self.active_alarms):
            self.active_alarms[alarm_index].acknowledged = True
            return True
        return False

    def get_tag_value(self, tag_name: str) -> TagValue | None:
        """Get current value of a tag."""
        return self.tags.get(tag_name)

    def get_historian_data(self, tag_name: str, limit: int = 100) -> list[dict]:
        """Get historical data for a tag."""
        return [
            entry for entry in list(self.historian)[-limit:] if entry["tag"] == tag_name
        ]

    def get_active_alarms(self) -> list[AlarmEvent]:
        """Get list of active alarms."""
        return self.active_alarms.copy()

    def get_alarm_summary(self) -> dict:
        """Get alarm summary for operator display."""
        return {
            "total_active": len(self.active_alarms),
            "unacknowledged": sum(1 for a in self.active_alarms if not a.acknowledged),
            "critical": sum(1 for a in self.active_alarms if a.priority == 1),
            "high": sum(1 for a in self.active_alarms if a.priority == 2),
            "active_alarms": [
                {
                    "tag": a.tag_name,
                    "value": a.value,
                    "limit": a.limit,
                    "type": a.alarm_type,
                    "priority": a.priority,
                    "acknowledged": a.acknowledged,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.active_alarms
            ],
        }
