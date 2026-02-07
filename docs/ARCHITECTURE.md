# Power and Light Simulator - Architecture Documentation

Architecture of the Power and Light ICS Simulator, including both implemented and partially-integrated components. 
It serves as a reference for understanding dependencies and identifying architectural inconsistencies.

## Overview

### Design philosophy

The simulator is designed around the following principles:

1. Configuration-Driven: YAML files define devices, networks, and protocols
2. Protocol-Agnostic: Devices expose memory maps independent of protocol implementation
3. Physics-Aware: Real-time physics engines simulate industrial process behaviour
4. Time-Aware: Unified simulation time management across all components
5. Security-Focused: Comprehensive logging and audit trail for research purposes
6. Async-First: All I/O operations use async/await for concurrent execution

### High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration Layer                          │
│              (YAML files → ConfigLoader)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                    Orchestration Layer                          │
│                   (SimulatorManager)                            │
│  - Initialisation and lifecycle management                     │
│  - Component coordination                                      │
└────┬─────────┬──────────┬───────────┬──────────┬──────────────┘
     │         │          │           │          │
     ▼         ▼          ▼           ▼          ▼
┌─────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────────────┐
│ Devices │ │Physics │ │ Network │ │Protocol│ │   Security   │
│ Layer   │ │Engines │ │  Sim    │ │Servers │ │   & Logging  │
└────┬────┘ └───┬────┘ └────┬────┘ └───┬────┘ └──────┬───────┘
     │          │           │          │             │
     └──────────┴───────────┴──────────┴─────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   State Management     │
              │ (DataStore/SystemState)│
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   SimulationTime       │
              │     (Singleton)        │
              └────────────────────────┘
```

### External interface Boundary (Black Box Design)

Critical Architectural Principle: External clients (attack scripts, operators, security tools) interact with the simulator ONLY through standard industrial protocols. They have NO knowledge of internal Python classes.

```
┌──────────────────────────────────────────────────────────────┐
│  EXTERNAL WORLD (Black Box)                                  │
│                                                              │
│  - Attack scripts (Python, Metasploit, etc.)                 │
│  - Operator HMI applications                                 │
│  - Security tools (Nmap, ICS scanners)                       │
│  - SCADA clients                                             │
│                                                              │
│  Knowledge: ONLY standard protocols (Modbus, OPC UA, etc.)   │
│  No access to: BaseDevice, DataStore, Python internals       │
└──────────────────────┬───────────────────────────────────────┘
                       │
            Network (TCP/UDP/Serial)
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  PROTOCOL BOUNDARY (Protocol Servers)                        │
│                                                              │
│  ┌────────────┐ ┌─────────┐ ┌──────┐ ┌────────┐              │
│  │ Modbus TCP │ │ OPC UA  │ │ DNP3 │ │ IEC104 │  ...         │
│  │   :502     │ │  :4840  │ │:20000│ │ :2404  │              │
│  └─────┬──────┘ └────┬────┘ └───┬──┘ └───┬────┘              │
│        │             │          │        │                   │
│        └─────────────┴──────────┴────────┘                   │
│                       │                                      │
│              DataStore Interface                             │
│                       │                                      │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│  INTERNAL IMPLEMENTATION (Hidden from External)              │
│                                                              │
│  - BaseDevice, BasePhysicsEngine                             │
│  - DataStore, SystemState, SimulationTime                    │
│  - ICSLogger, NetworkSimulator                               │
│  - Device-specific logic (TurbinePLC, ReactorPLC, etc.)      │
│                                                              │
│  These are Python implementation details, not exposed        │
└──────────────────────────────────────────────────────────────┘
```

#### Important for

1. Realistic attack simulation
   - Attackers use standard ICS protocols (exactly as in real systems)
   - Attack scripts work against real devices AND this simulator
   - No "simulator-specific" attack code needed

2. Tool compatibility
   - Standard tools work: Metasploit modules, Nmap NSE scripts, etc.
   - Security researchers use familiar tools
   - No need to learn simulator internals

3. Protocol fidelity
   - Forces correct protocol implementation
   - Devices must behave like real ICS equipment
   - No shortcuts or simulator-specific backdoors

4. Separation of concerns
   - Internal refactoring doesn't affect external interface
   - Can swap device implementations without changing protocols
   - Physics engines can be modified independently

## Component organisation

### Directory structure

```
power-and-light-sim/
├── components/              # Core simulation engine
│   ├── devices/            # Device implementations
│   │   ├── core/          # BaseDevice abstract base class
│   │   ├── control_zone/  # Field devices (PLCs, RTUs, Safety)
│   │   ├── operations_zone/  # SCADA, HMI, Engineering stations
│   │   └── enterprise_zone/  # Historian, IDS, SIEM
│   ├── protocols/          # Protocol abstractions
│   │   ├── base_protocol.py   # Abstract protocol interface
│   │   ├── modbus/         # Modbus TCP/RTU implementation
│   │   ├── dnp3/           # DNP3 implementation
│   │   ├── iec104/         # IEC 60870-5-104 implementation
│   │   ├── iec61850/       # IEC 61850 MMS & GOOSE
│   │   ├── opcua/          # OPC UA implementation
│   │   └── s7/             # Siemens S7 implementation
│   ├── network/            # Network simulation
│   │   ├── network_simulator.py  # Topology enforcement
│   │   ├── protocol_simulator.py # Protocol routing
│   │   ├── tcp_proxy.py        # Network interception
│   │   └── servers/        # Protocol server implementations
│   ├── physics/            # Physics engines
│   │   ├── turbine_physics.py   # Steam turbine dynamics
│   │   ├── reactor_physics.py   # Nuclear reactor simulation
│   │   ├── hvac_physics.py      # HVAC system dynamics
│   │   ├── grid_physics.py      # Electrical grid state
│   │   └── power_flow.py        # Power flow analysis
│   ├── state/              # State management
│   │   ├── system_state.py    # Centralised state (singleton)
│   │   └── data_store.py      # Device memory interface
│   ├── security/           # Security & monitoring
│   │   ├── logging_system.py  # ICSLogger (structured logging)
│   │   ├── authentication.py  # Auth manager
│   │   ├── encryption.py      # Certificate/key management
│   │   └── anomaly_detector.py  # Security analytics
│   └── time/               # Simulation timing
│       └── simulation_time.py  # Time management (singleton)
├── config/                # Configuration files
│   ├── config_loader.py   # Modular YAML loader
│   ├── devices.yml        # Device definitions
│   ├── network.yml        # Network topology (Purdue model)
│   ├── protocols.yml      # Protocol settings
│   ├── simulation.yml     # Runtime settings
│   ├── scada_tags.yml     # SCADA tag definitions
│   ├── hmi_screens.yml    # HMI screen layouts
│   └── device_identity.yml  # Device identities
├── tools/
│   └── simulator_manager.py  # Main orchestrator
└── tests/
    ├── unit/              # Unit tests
    └── functional/        # Integration tests
```

## Core abstractions

### BaseDevice

The foundation for all device implementations.

```python
class BaseDevice(ABC):
    """Abstract base class for all simulated ICS devices."""

    # Properties
    device_name: str          # Unique identifier
    device_id: int           # Numeric ID
    device_type: str         # Type identifier
    memory_map: dict         # Protocol-agnostic memory storage
    data_store: DataStore    # Reference to state manager
    scan_interval: float     # Scan cycle period (seconds)
    sim_time: SimulationTime # Time reference
    metadata: dict           # Diagnostic information

    # Abstract Methods (must implement)
    @abstractmethod
    def _device_type(self) -> str:
        """Return device type identifier."""

    @abstractmethod
    def _supported_protocols(self) -> list[str]:
        """Return list of supported protocol names."""

    @abstractmethod
    async def _initialise_memory_map(self) -> None:
        """Initialise device memory map."""

    @abstractmethod
    async def _scan_cycle(self) -> None:
        """Execute one scan cycle."""

    # Lifecycle Methods
    async def start(self) -> None:
        """Start device operation."""
        # 1. Initialise memory map
        # 2. Register with DataStore
        # 3. Start scan loop

    async def stop(self) -> None:
        """Stop device operation."""
        # 1. Cancel scan loop
        # 2. Mark offline in DataStore

    async def reset(self) -> None:
        """Reset device to initial state."""
        # 1. Stop device
        # 2. Reinitialise memory map
        # 3. Restart device

    # Memory Map Interface
    def read_memory(self, address: str) -> Any:
        """Read from memory map."""

    def write_memory(self, address: str, value: Any) -> bool:
        """Write to memory map."""

    def bulk_read_memory(self) -> dict:
        """Read entire memory map."""

    def bulk_write_memory(self, updates: dict) -> bool:
        """Bulk write to memory map."""

    # Status Methods
    def is_online(self) -> bool:
        """Check if device is online."""

    def is_running(self) -> bool:
        """Check if scan loop is running."""

    async def get_status(self) -> dict:
        """Get device status."""
```

#### Device hierarchy

```
BaseDevice (abstract)
├── BasePLC (abstract)
│   ├── TurbinePLC
│   ├── HVACPLC
│   ├── ReactorPLC
│   ├── S7PLC
│   └── ABLogixPLC
├── BaseRTU (abstract)
│   └── SubstationRTU
├── BaseSafetyController (abstract)
│   ├── SISController
│   ├── ReactorSafetyPLC
│   └── TurbineSafetyPLC
├── BaseSupervisoryDevice (abstract)
│   └── SCADAServer
├── BaseEnterpriseDevice (inherits BaseDevice directly)
│   ├── Historian (multi-protocol: OPC UA, SQL, HTTP, ODBC)
│   ├── IDSSystem (network-based IDS)
│   ├── SIEMSystem (security information & event management)
│   └── SubstationController (IEC 61850, IEC-104, Modbus)
├── BaseWorkstation (inherits BaseDevice directly)
│   ├── HMIWorkstation
│   ├── EngineeringWorkstation
│   ├── LegacyWorkstation (Windows 98, SMBv1, serial)
│   └── EnterpriseWorkstation (phishing target)
└── Smart Grid Devices
    └── IED (Intelligent Electronic Device - protection relays)
```

### BaseProtocol

The foundation for all protocol implementations.

```python
class BaseProtocol(ABC):
    """Abstract base class for protocol implementations."""

    # Properties
    protocol_name: str
    connected: bool

    # Abstract Methods
    @abstractmethod
    async def connect(self) -> bool:
        """Establish protocol connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close protocol connection."""

    @abstractmethod
    async def probe(self) -> dict[str, object]:
        """Probe protocol capabilities (for attack research)."""
```

#### Protocol architecture pattern

```
BaseProtocol (abstract wrapper)
    ↓
Protocol Implementation (for example ModbusProtocol)
    ↓
Adapter Layer (for example ModbusTCPAdapter)
    ↓
Third-Party Library (for example pymodbus)
    ↓
Network
```

Example:
```python
# ModbusProtocol wraps ModbusTCPAdapter
# ModbusTCPAdapter wraps pymodbus.client.AsyncModbusTcpClient

class ModbusProtocol(BaseProtocol):
    def __init__(self, adapter: ModbusTCPAdapter):
        super().__init__("modbus")
        self.adapter = adapter

    async def connect(self) -> bool:
        return await self.adapter.connect()

    async def read_holding_registers(self, address: int, count: int):
        return await self.adapter.read_holding_registers(address, count)
```

### State Management

#### SystemState (Singleton)

Centralised state storage for all devices.

```python
class SystemState:
    """Centralised state storage (singleton pattern)."""

    # Properties
    devices: dict[str, DeviceState]  # device_name → DeviceState
    simulation: SimulationState
    _lock: asyncio.Lock  # Thread-safe access

    # Methods
    async def register_device(self, device: DeviceState) -> None:
        """Register a device."""

    async def update_device(self, device_name: str, kwargs) -> None:
        """Update device state."""

    async def get_device(self, device_name: str) -> DeviceState | None:
        """Get device state."""
```

#### DeviceState (Dataclass)

```python
@dataclass
class DeviceState:
    """State representation for a single device."""

    device_name: str
    device_type: str
    device_id: int
    protocols: list[str]
    online: bool
    memory_map: dict[str, Any]
    last_update: datetime
    metadata: dict[str, Any]
```

#### DataStore (Interface)

Provides convenient interface over SystemState.

```python
class DataStore:
    """Interface for device state operations."""

    def __init__(self, system_state: SystemState):
        self.system_state = system_state

    async def register_device(self, device_info: dict) -> None:
        """Register device with state manager."""

    async def read_memory(
        self, device_name: str, address: str
    ) -> Any | None:
        """Read memory value from device."""

    async def write_memory(
        self, device_name: str, address: str, value: Any
    ) -> bool:
        """Write memory value to device."""

    async def bulk_read_memory(self, device_name: str) -> dict:
        """Read entire memory map."""

    async def bulk_write_memory(
        self, device_name: str, updates: dict
    ) -> bool:
        """Bulk write to memory map."""
```

### 4. SimulationTime (Singleton)

Unified time management for all components.

```python
class SimulationTime:
    """Singleton time manager with multiple operation modes."""

    # Operation Modes
    REALTIME = "realtime"      # 1:1 with wall clock
    ACCELERATED = "accelerated"  # N:1 speed multiplier
    STEPPED = "stepped"        # Manual step() calls
    PAUSED = "paused"          # Paused state

    # Methods
    def now(self) -> float:
        """Get current simulation time."""

    def delta(self, last_time: float) -> float:
        """Calculate elapsed time since last_time."""

    def is_paused(self) -> bool:
        """Check if simulation is paused."""

    async def set_speed(self, multiplier: float) -> None:
        """Set time acceleration multiplier."""

    async def pause(self) -> None:
        """Pause simulation time."""

    async def resume(self) -> None:
        """Resume simulation time."""

    async def step(self, delta_seconds: float) -> None:
        """Step simulation forward (STEPPED mode only)."""
```

## Subsystem details

### Device subsystem

#### Device scan cycle

All devices follow a consistent scan cycle pattern:

```
┌─────────────────────────────────────────────────────────────┐
│ Device Scan Cycle (runs at scan_interval frequency)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. Check if simulation is paused                            │
│    → If paused, skip this cycle                             │
│                                                             │
│ 2. Read protocol writes from DataStore                      │
│    memory_updates = await data_store.bulk_read_memory()     │
│    memory_map.update(memory_updates)                        │
│    → Get any writes from network (Modbus/OPC UA clients)    │
│                                                             │
│ 3. Execute device-specific scan logic                       │
│    await self._scan_cycle()                                 │
│    → For PLCs: _read_inputs() → _execute_logic()            │
│                → _write_outputs()                           │
│    → For RTUs: poll_substations()                           │
│    → For SCADA: aggregate_telemetry()                       │
│                                                             │
│ 4. Write device outputs to DataStore                        │
│    await data_store.bulk_write_memory(memory_map)           │
│    → Publish telemetry for protocol servers to read         │
│                                                             │
│ 5. Update metadata (scan count, error count, timestamp)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### PLC scan cycle pattern

PLCs implement a more specific scan pattern:

```python
class BasePLC(BaseDevice):
    """Base class for PLC implementations."""

    async def _scan_cycle(self) -> None:
        """Standard PLC scan cycle."""
        await self._read_inputs()
        await self._execute_logic()
        await self._write_outputs()

    @abstractmethod
    async def _read_inputs(self) -> None:
        """Read inputs from physics engines."""
        # Example: Read turbine state
        # turbine_state = self.turbine_physics.get_state()
        # self.memory_map["input_registers[0]"] = turbine_state.speed

    @abstractmethod
    async def _execute_logic(self) -> None:
        """Execute PLC ladder logic or control algorithms."""
        # Example: PID control
        # setpoint = self.memory_map["holding_registers[0]"]
        # current = self.memory_map["input_registers[0]"]
        # output = self.pid_controller.update(setpoint, current)
        # self.memory_map["holding_registers[1]"] = output

    @abstractmethod
    async def _write_outputs(self) -> None:
        """Write outputs to physics engines."""
        # Example: Update turbine controls
        # control_signal = self.memory_map["holding_registers[1]"]
        # self.turbine_physics.set_control(control_signal)
```

#### Memory map convention

Devices use protocol-agnostic memory maps that are mapped to protocol-specific addresses:

```python
# Modbus addressing
memory_map = {
    "holding_registers[0]": 3600,    # Speed setpoint (RPM)
    "holding_registers[1]": 85,      # Governor position (%)
    "input_registers[0]": 3585,      # Actual speed (RPM)
    "input_registers[1]": 450,       # Temperature (°C)
    "coils[0]": True,                # Governor enable
    "coils[1]": False,               # Emergency stop
    "discrete_inputs[0]": True,      # Turbine running
    "discrete_inputs[1]": False,     # Overspeed alarm
}

# OPC UA addressing (tag-based)
memory_map = {
    "ns=2;s=SpeedSetpoint": 3600,
    "ns=2;s=ActualSpeed": 3585,
    "ns=2;s=Temperature": 450,
    "ns=2;s=GovernorEnable": True,
}

# IEC 104 addressing (type + address)
memory_map = {
    "M_ME_NC_1:100": 3585.0,   # Measured value, short floating point
    "M_SP_NA_1:0": True,        # Single point status
}
```

### Protocol subsystem

#### Protocol server architecture

Protocol servers bridge devices and the network:

```
┌──────────────────────────────────────────────────┐
│ Protocol Server (for example ModbusTCPServer)    │
├──────────────────────────────────────────────────┤
│ Role: Expose device memory maps via network      │
│                                                  │
│ 1. Listen on network port (e.g., localhost:502)  │
│                                                  │
│ 2. Periodic sync with device (every scan):       │
│    - Read device memory_map from DataStore       │
│    - Update protocol server's internal state     │
│                                                  │
│ 3. Handle client requests:                       │
│    - READ: Return values from internal state     │
│    - WRITE: Update internal state + DataStore    │
│                                                  │
│ 4. Network isolation (via NetworkSimulator):     │
│    - Validate client can reach device            │
│    - Enforce zone-based security policies        │
└──────────────────────────────────────────────────┘
```

#### Implemented protocol servers

| Protocol    | Port   | Status   | Library Used    | Test Coverage |
|-------------|--------|----------|-----------------|---------------|
| Modbus TCP  | 502    | Complete | pymodbus 3.11.4 | 71 unit tests |
| Modbus RTU  | Serial | Complete | pymodbus 3.11.4 | 71 unit tests |
| DNP3        | 20000  | Partial  | dnp3py          | 37 unit tests |
| IEC 104     | 2404   | Complete | c104 2.2.1      | 44 unit tests |
| OPC UA      | 4840   | Complete | asyncua         | Integrated    |
| S7          | 102    | Complete | snap7           | Integrated    |
| EtherNet/IP | 44818  | Partial  | cpppo           | Integrated    |

### Physics subsystem

#### Physics engine pattern

Physics engines simulate real-world process behaviour:

```python
class TurbinePhysics:
    """Steam turbine physics simulation."""

    def __init__(self, config: dict):
        # State variables
        self.shaft_speed = 0.0      # RPM
        self.temperature = 25.0     # °C
        self.vibration = 0.0        # mm/s
        self.pressure = 0.0         # bar

        # Control inputs
        self.governor_position = 0.0  # %
        self.steam_valve = 0.0        # %

        # Physics parameters
        self.inertia = config.get("inertia", 1000.0)
        self.friction = config.get("friction", 0.1)

    def get_state(self) -> dict:
        """Get current physics state."""
        return {
            "shaft_speed": self.shaft_speed,
            "temperature": self.temperature,
            "vibration": self.vibration,
            "pressure": self.pressure,
        }

    def set_control(self, governor_position: float, steam_valve: float):
        """Set control inputs."""
        self.governor_position = governor_position
        self.steam_valve = steam_valve

    def update(self, dt: float):
        """Update physics state (called every simulation step)."""
        # Implement differential equations
        # dω/dt = (Torque - Friction) / Inertia
        torque = self.steam_valve * 100.0
        friction_torque = self.friction * self.shaft_speed
        acceleration = (torque - friction_torque) / self.inertia
        self.shaft_speed += acceleration * dt

        # Update temperature based on speed
        self.temperature = 25.0 + (self.shaft_speed / 100.0)

        # Update vibration
        self.vibration = abs(self.shaft_speed - 3600) * 0.01
```

#### Implemented physics engines

| Engine         | Purpose                    | State Variables                                | Integration Status |
|----------------|----------------------------|------------------------------------------------|--------------------|
| TurbinePhysics | Steam turbine dynamics     | Speed, temperature, vibration, pressure        | Complete           |
| ReactorPhysics | Nuclear reactor simulation | Power level, temperature, pressure, reactivity | Complete           |
| HVACPhysics    | HVAC system dynamics       | Temperature, humidity, airflow, pressure       | Complete           |
| GridPhysics    | Electrical grid state      | Voltage, frequency, power flow                 | Complete           |
| PowerFlow      | Steady-state power flow    | Bus voltages, line flows, generator output     | Complete           |

Physics engines inherit from `BasePhysicsEngine` (system-wide engines) or `BaseDevicePhysicsEngine` 
(device-specific engines), providing:
- Unified lifecycle management (`initialise()`, `update(dt)`)
- Common state access interface (`get_state()`, `get_telemetry()`)
- Validation patterns (`_validate_update()`)
- ICSLogger integration
- SimulationTime and DataStore integration

### Network topology model (Purdue Model)

```
┌─────────────────────────────────────────────────┐
│ Enterprise Zone (Level 4-5)                     │
│ - Enterprise workstations                       │
│ - Corporate applications                        │
│ - Internet gateway                              │
└────────────────┬────────────────────────────────┘
                 │
            ┌────▼─────────┐
            │     DMZ      │  (Firewalls, proxies)
            └────┬─────────┘
                 │
┌────────────────▼────────────────────────────────┐
│ Operations Zone (Level 3)                       │
│ - SCADA servers                                 │
│ - HMI workstations                              │
│ - Engineering workstations                      │
│ - Historian                                     │
│ - IDS/SIEM                                      │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│ Control Zone (Level 1-2)                        │
│ - PLCs                                          │
│ - RTUs                                          │
│ - Safety controllers                            │
│ - Field devices                                 │
└─────────────────────────────────────────────────┘
```

Status: Enforced
- Topology definition: Complete
- Device network membership: Complete
- Basic reachability checks: Complete
- Zone security policies: Enforced (Purdue Model)
- Firewall rules: Port-based filtering implemented
- Protocol restrictions: Per-zone protocol allowlists
- Network latency/jitter: Not implemented yet

## Dependency graph

### Component dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                     No Dependencies                         │
│                                                             │
│  SimulationTime (singleton)                                 │
│  ConfigLoader                                               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Level 1: State                            │
│                                                             │
│  SystemState (singleton) ← SimulationTime                   │
│  DataStore ← SystemState                                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Level 2: Infrastructure                   │
│                                                             │
│  ICSLogger ← SimulationTime, DataStore (optional)           │
│  NetworkSimulator ← ConfigLoader, SystemState               │
│  Authentication ← DataStore                                 │
│  Encryption                                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Level 3: Physics & Protocols              │
│                                                             │
│  Physics Engines ← SimulationTime, DataStore                │
│  Protocol Adapters ← Third-party libraries                  │
│  Protocols ← Adapters                                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Level 4: Devices                          │
│                                                             │
│  BaseDevice ← DataStore, SimulationTime, ICSLogger          │
│  Device Implementations ← BaseDevice, Physics Engines       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Level 5: Network Services                 │
│                                                             │
│  Protocol Servers ← Devices (via DataStore), Protocols      │
│  ProtocolSimulator ← NetworkSimulator, Protocol Servers     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Level 6: Orchestration                    │
│                                                             │
│  SimulatorManager ← All components                          │
└─────────────────────────────────────────────────────────────┘
```

### Critical pependency rules

1. No Circular Dependencies: The architecture enforces a strict directed acyclic graph (DAG)
2. Singleton Management: SimulationTime and SystemState are singletons with async-safe initialisation
3. DataStore as Hub: All state reads/writes go through DataStore
4. Time Authority: All time queries use SimulationTime.now()
5. Config-Driven: Device instantiation uses DEVICE_REGISTRY from config

## Data flow

### Initialisation flow

```
1. ConfigLoader.load_config()
   ├→ Load devices.yml
   ├→ Load network.yml
   ├→ Load protocols.yml
   └→ Load simulation.yml

2. SimulatorManager.initialise()
   ├→ SimulationTime.get_instance()
   ├→ SystemState (create)
   ├→ DataStore(system_state)
   ├→ NetworkSimulator(config)
   ├→ Physics engines (create)
   └→ Instantiate devices from DEVICE_REGISTRY

3. SimulationTime.start()
   └→ Begin time tracking

4. For each device:
   ├→ await device.start()
   │  ├→ await _initialise_memory_map()
   │  ├→ await data_store.register_device()
   │  ├→ await data_store.bulk_write_memory()
   │  └→ Start _scan_loop() task
   └→ Device enters scan cycle

5. Protocol servers start
   ├→ Listen on network ports
   └→ Begin syncing with devices

6. SimulatorManager enters main loop
   └→ Monitor and coordinate components
```

### Runtime data flow (per scan cycle)

```
┌──────────────────────────────────────────────────────────┐
│ Network Clients (Attackers/Operators)                    │
│ Write commands via Modbus/OPC UA/etc.                    │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ Protocol Servers                                         │
│ Receive writes → Update DataStore                        │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ DataStore (SystemState)                                  │
│ Store updated memory map values                          │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ Device Scan Cycle                                        │
│ 1. Read from DataStore (get protocol writes)             │
│ 2. _read_inputs() - Read physics state                   │
│ 3. _execute_logic() - PLC logic/control algorithms       │
│ 4. _write_outputs() - Update physics controls            │
│ 5. Write to DataStore (publish outputs)                  │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ Physics Engines                                          │
│ Update state based on control inputs                     │
│ Simulate real-world process behaviour                    │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼ (next cycle)
┌──────────────────────────────────────────────────────────┐
│ DataStore                                                │
│ Device writes outputs (telemetry, alarms)                │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ Protocol Servers                                         │
│ Sync with DataStore → Update internal state              │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ Network Clients                                          │
│ Read telemetry via protocols                             │
└──────────────────────────────────────────────────────────┘
```

## Design patterns

### Patterns used

| Pattern             | Usage                                            | Location                                            |
|---------------------|--------------------------------------------------|-----------------------------------------------------|
| Singleton           | SimulationTime, SystemState                      | `components/time/`, `components/state/`             |
| Factory             | `get_logger()`, DEVICE_REGISTRY                  | `components/security/`, `components/__init__.py`    |
| Abstract Base Class | BaseDevice, BaseProtocol                         | `components/devices/core/`, `components/protocols/` |
| Adapter             | Protocol adapters wrap third-party libraries     | `components/protocols/*/`                           |
| Facade              | DataStore simplifies SystemState access          | `components/state/`                                 |
| Observer            | Protocol servers observe device state changes    | `components/network/servers/`                       |
| Strategy            | Different time modes in SimulationTime           | `components/time/`                                  |
| Registry            | DEVICE_REGISTRY for dynamic device instantiation | `components/__init__.py`                            |

### Anti-patterns

1. Circular Dependencies: Strictly forbidden (enforced by layered architecture)
2. God Objects: Avoid putting too much logic in SimulatorManager
3. Tight Coupling: Always use DataStore, never direct device references
4. Blocking I/O in Async: Always await or use asyncio.to_thread()

## Configuration files

See `config/`

## Summary

1. Well-designed abstractions (BaseDevice, BaseProtocol)
2. Configuration-driven architecture (YAML configs)
3. Unified time management (SimulationTime singleton)
4. Centralised state (DataStore/SystemState)
5. Protocol-agnostic device memory maps
6. Physics-aware simulation
7. Async/await throughout
8. Modular and extensible

Last Updated: February 2026

