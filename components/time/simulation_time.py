import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from config.config_loader import ConfigLoader


# ----------------------------------------------------------------
# Time modes
# ----------------------------------------------------------------
class TimeMode(Enum):
    REALTIME = "realtime"
    ACCELERATED = "accelerated"
    STEPPED = "stepped"
    PAUSED = "paused"


@dataclass
class TimeState:
    simulation_time: float = 0.0
    wall_time_start: float = 0.0
    wall_time_elapsed: float = 0.0
    mode: TimeMode = TimeMode.REALTIME
    speed_multiplier: float = 1.0
    paused: bool = False
    update_interval: float = 0.01  # default, overridden by YAML


# ----------------------------------------------------------------
# Singleton simulation time manager
# ----------------------------------------------------------------
class SimulationTime:
    _instance: Optional["SimulationTime"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.state = TimeState()
        self._lock = asyncio.Lock()
        self._running = False
        self._update_task: asyncio.Task | None = None

        # Load from YAML
        config = ConfigLoader().load_all()
        runtime_cfg = config.get("simulation", {}).get("runtime", {})

        # Set update interval
        self.state.update_interval = runtime_cfg.get("update_interval", 0.01)

        # Set initial mode
        if runtime_cfg.get("realtime", True):
            self.state.mode = TimeMode.REALTIME
        else:
            self.state.mode = TimeMode.ACCELERATED

        # Set speed multiplier
        self.state.speed_multiplier = runtime_cfg.get("time_acceleration", 1.0)

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------
    async def start(self):
        if self._running:
            return

        async with self._lock:
            self.state.wall_time_start = time.time()
            self.state.simulation_time = 0.0
            self.state.wall_time_elapsed = 0.0
            self.state.paused = self.state.mode == TimeMode.PAUSED

        self._running = True

        if self.state.mode in [TimeMode.REALTIME, TimeMode.ACCELERATED]:
            self._update_task = asyncio.create_task(self._time_loop())

    async def stop(self):
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None

    async def reset(self):
        async with self._lock:
            self.state.simulation_time = 0.0
            self.state.wall_time_start = time.time()
            self.state.wall_time_elapsed = 0.0

    # ----------------------------------------------------------------
    # Time queries
    # ----------------------------------------------------------------
    def now(self) -> float:
        return self.state.simulation_time

    def delta(self, last_time: float) -> float:
        return self.state.simulation_time - last_time

    def elapsed(self) -> float:
        return self.state.simulation_time

    def wall_elapsed(self) -> float:
        return self.state.wall_time_elapsed

    def speed(self) -> float:
        return self.state.speed_multiplier

    def is_paused(self) -> bool:
        return self.state.paused

    # ----------------------------------------------------------------
    # Time control
    # ----------------------------------------------------------------
    async def pause(self):
        async with self._lock:
            self.state.paused = True

    async def resume(self):
        async with self._lock:
            self.state.paused = False
            self.state.wall_time_start = time.time() - (
                self.state.simulation_time / self.state.speed_multiplier
            )

    async def set_speed(self, multiplier: float):
        async with self._lock:
            current_sim_time = self.state.simulation_time
            self.state.speed_multiplier = multiplier
            self.state.wall_time_start = time.time() - (current_sim_time / multiplier)

    async def step(self, delta_seconds: float):
        async with self._lock:
            if self.state.mode != TimeMode.STEPPED:
                raise RuntimeError("step() only valid in STEPPED mode")
            self.state.simulation_time += delta_seconds
            self.state.wall_time_elapsed = time.time() - self.state.wall_time_start

    # ----------------------------------------------------------------
    # Internal time loop
    # ----------------------------------------------------------------
    async def _time_loop(self):
        last_update = time.time()
        interval = self.state.update_interval

        while self._running:
            await asyncio.sleep(interval)
            current_time = time.time()

            async with self._lock:
                if self.state.paused:
                    last_update = current_time
                    continue

                wall_delta = current_time - last_update
                last_update = current_time
                sim_delta = wall_delta * self.state.speed_multiplier
                self.state.simulation_time += sim_delta
                self.state.wall_time_elapsed = current_time - self.state.wall_time_start

    # ----------------------------------------------------------------
    # Status
    # ----------------------------------------------------------------
    async def get_status(self) -> dict:
        async with self._lock:
            return {
                "simulation_time": self.state.simulation_time,
                "wall_time_elapsed": self.state.wall_time_elapsed,
                "mode": self.state.mode.value,
                "speed_multiplier": self.state.speed_multiplier,
                "paused": self.state.paused,
                "ratio": (
                    self.state.simulation_time / self.state.wall_time_elapsed
                    if self.state.wall_time_elapsed > 0
                    else 0.0
                ),
            }


# ----------------------------------------------------------------
# Convenience functions
# ----------------------------------------------------------------
async def wait_simulation_time(seconds: float):
    sim_time = SimulationTime()
    start_time = sim_time.now()
    target_time = start_time + seconds

    while sim_time.now() < target_time:
        await asyncio.sleep(sim_time.state.update_interval)
        if sim_time.is_paused():
            await asyncio.sleep(sim_time.state.update_interval * 10)


def get_simulation_delta(last_time: float) -> float:
    sim_time = SimulationTime()
    return sim_time.delta(last_time)
