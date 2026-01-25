#!/usr/bin/env python3
"""
Async simulator manager with multi-protocol support.
"""

import asyncio
import importlib
from pathlib import Path
from typing import Any

import yaml
from components.adapters.c104_221 import IEC104C104Adapter
from components.adapters.opcua_asyncua_118 import OPCUAAsyncua118Adapter
from components.adapters.pymodbus_3114 import PyModbus3114Adapter
from components.adapters.snap7_202 import Snap7Adapter202
from components.protocols.iec104_protocol import IEC104Protocol
from components.protocols.modbus_protocol import ModbusProtocol
from components.protocols.opcua_protocol import OPCUAProtocol
from components.protocols.s7_protocol import S7Protocol
from config.config_loader import ConfigLoader

# Map of adapter classes (only include available adapters)
ADAPTER_REGISTRY = {}
if PyModbus3114Adapter:
    ADAPTER_REGISTRY["pymodbus_3114"] = PyModbus3114Adapter
if IEC104C104Adapter:
    ADAPTER_REGISTRY["c104_221"] = IEC104C104Adapter
if Snap7Adapter202:
    ADAPTER_REGISTRY["snap7_202"] = Snap7Adapter202
if OPCUAAsyncua118Adapter:
    ADAPTER_REGISTRY["opcua_asyncua_118"] = OPCUAAsyncua118Adapter

# Protocol wrapper classes
PROTOCOL_REGISTRY = {
    "modbus": ModbusProtocol,
    "iec104": IEC104Protocol,
    "s7": S7Protocol,
    "opcua": OPCUAProtocol,
}

# Device class registry - maps device type to Python class path
DEVICE_REGISTRY = {
    # PLCs
    "turbine_plc": "components.devices.plc.turbine_plc.TurbinePLC",
    "substation_plc": "components.devices.plc.substation_plc.SubstationPLC",
    "modbus_plc": "components.devices.plc.modbus_plc.ModbusPLC",
    "s7_plc": "components.devices.plc.s7_plc.S7PLC",
    "ab_logix_plc": "components.devices.plc.ab_logix_plc.ABLogixPLC",
    # RTUs
    "rtu_c104": "components.devices.rtu_c104.RTUC104",
    "rtu_modbus": "components.devices.rtu_modbus.RTUModbus",
    # Substation devices
    "ied": "components.devices.ied.IED",
    "substation_controller": "components.devices.substation_controller.SubstationController",
    "sis_controller": "components.devices.sis_controller.SISController",
    # SCADA and monitoring
    "scada_server": "components.devices.scada_server.SCADAServer",
    "historian": "components.devices.historian.Historian",
    # Workstations
    "engineering_workstation": "components.devices.engineering_workstation.EngineeringWorkstation",
    "hmi_workstation": "components.devices.hmi_workstation.HMIWorkstation",
    # Security
    "ids_system": "components.devices.ids_system.IDSSystem",
    "siem_system": "components.devices.siem_system.SIEMSystem",
}


class AsyncSimulatorManager:
    """Manager for async simulator with multi-protocol adapter abstraction."""

    def __init__(self, config_path: str = "config/network.yml"):
        self.config_path = Path(config_path)
        self.devices = {}
        self.running = False
        self.config_loader = ConfigLoader(config_dir="config")

    @staticmethod
    def _load_device_class(device_type: str):
        """Load a device class from registry."""
        cls_path = DEVICE_REGISTRY.get(device_type)
        if not cls_path:
            raise RuntimeError(f"No device class registered for type '{device_type}'")

        module_path, class_name = cls_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    @staticmethod
    def _create_modbus_adapter(
        device_cfg: dict[str, Any], device_class
    ) -> PyModbus3114Adapter:
        """Create a Modbus adapter with device-specific setup."""
        adapter_key = device_cfg.get("adapter", "pymodbus_3114")
        adapter_class = ADAPTER_REGISTRY.get(adapter_key)
        if not adapter_class:
            raise RuntimeError(f"No adapter registered under key '{adapter_key}'")

        # Get device's default setup
        device_setup = getattr(device_class, "DEFAULT_SETUP", None)
        if device_setup is None:
            raise RuntimeError(
                f"Device class {device_class.__name__} has no DEFAULT_SETUP defined"
            )

        return adapter_class(
            host=device_cfg.get("host", "localhost"),
            port=device_cfg.get("port", 5020),
            device_id=device_cfg.get("device_id", 1),
            simulator_mode=device_cfg.get("simulator", True),
            setup=device_setup.copy(),
        )

    @staticmethod
    def _create_iec104_adapter(device_cfg: dict[str, Any]) -> IEC104C104Adapter:
        """Create an IEC-104 adapter."""
        adapter_key = device_cfg.get("adapter", "c104_221")
        adapter_class = ADAPTER_REGISTRY.get(adapter_key)
        if not adapter_class:
            raise RuntimeError(f"No adapter registered under key '{adapter_key}'")

        return adapter_class(
            bind_host=device_cfg.get("bind_host", "0.0.0.0"),
            bind_port=device_cfg.get("bind_port", 2404),
            common_address=device_cfg.get("common_address", 1),
            simulator_mode=device_cfg.get("simulator", True),
        )

    @staticmethod
    def _create_s7_adapter(device_cfg: dict[str, Any]) -> Snap7Adapter202:
        """Create an S7 adapter."""
        adapter_key = device_cfg.get("adapter", "snap7_202")
        adapter_class = ADAPTER_REGISTRY.get(adapter_key)
        if not adapter_class:
            raise RuntimeError(f"No adapter registered under key '{adapter_key}'")

        return adapter_class(
            host=device_cfg.get("host", "localhost"),
            rack=device_cfg.get("rack", 0),
            slot=device_cfg.get("slot", 1),
            simulator_mode=device_cfg.get("simulator", True),
        )

    @staticmethod
    def _create_opcua_adapter(device_cfg: dict[str, Any]) -> OPCUAAsyncua118Adapter:
        """Create an OPC UA adapter."""
        adapter_key = device_cfg.get("adapter", "opcua_asyncua_118")
        adapter_class = ADAPTER_REGISTRY.get(adapter_key)
        if not adapter_class:
            raise RuntimeError(f"No adapter registered under key '{adapter_key}'")

        return adapter_class(
            endpoint=device_cfg.get("endpoint", "opc.tcp://localhost:4840"),
            simulator_mode=device_cfg.get("simulator", True),
        )

    async def load_config(self) -> bool:
        """Load configuration and instantiate adapters + protocols."""
        if not self.config_path.exists():
            default_config = {
                "devices": [
                    {
                        "name": "turbine_plc_1",
                        "type": "turbine_plc",
                        "device_id": 1,
                        "description": "Main steam turbine PLC",
                        "protocols": {
                            "modbus": {
                                "adapter": "pymodbus_3114",
                                "host": "localhost",
                                "port": 15020,
                                "device_id": 1,
                                "simulator": True,
                            }
                        },
                    },
                    {
                        "name": "substation_plc_1",
                        "type": "substation_plc",
                        "device_id": 2,
                        "description": "Main substation PLC",
                        "protocols": {
                            "modbus": {
                                "adapter": "pymodbus_3114",
                                "host": "localhost",
                                "port": 15021,
                                "device_id": 2,
                                "simulator": True,
                            }
                        },
                    },
                    {
                        "name": "scada_server_1",
                        "type": "scada_server",
                        "device_id": 3,
                        "description": "SCADA master station",
                        "protocols": {
                            "modbus": {
                                "adapter": "pymodbus_3114",
                                "host": "localhost",
                                "port": 15022,
                                "device_id": 3,
                                "simulator": True,
                            }
                        },
                    },
                ]
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                yaml.dump(default_config, f)

            print(f"[INFO] Created default config at {self.config_path}")

        config = self.config_loader.load_all()
        devices_list = config.get("devices", [])

        if not devices_list:
            print("[WARN] No devices found in configuration")
            return True

        for device_cfg in devices_list:
            device_name = device_cfg.get("name")
            device_type = device_cfg.get("type")
            device_id = device_cfg.get("device_id", 1)
            description = device_cfg.get("description", "")
            protocols_cfg = device_cfg.get("protocols", {})

            if not device_name or not device_type:
                print(f"[WARN] Skipping invalid device config: {device_cfg}")
                continue

            print(f"[INFO] Loading device '{device_name}' (type: {device_type})")

            # Load device class
            try:
                device_class = self._load_device_class(device_type)
            except Exception as e:
                print(f"[ERROR] Failed to load device class '{device_type}': {e}")
                continue

            # Create adapters and protocols for each configured protocol
            protocols = {}
            adapters = {}

            for proto_name, proto_cfg in protocols_cfg.items():
                # Create adapter based on protocol type
                if proto_name == "modbus":
                    adapter = self._create_modbus_adapter(proto_cfg, device_class)
                    protocol = ModbusProtocol(adapter)
                elif proto_name == "iec104":
                    adapter = self._create_iec104_adapter(proto_cfg)
                    protocol = IEC104Protocol(adapter)
                elif proto_name == "s7":
                    adapter = self._create_s7_adapter(proto_cfg)
                    protocol = S7Protocol(adapter)
                elif proto_name == "opcua":
                    adapter = self._create_opcua_adapter(proto_cfg)
                    protocol = OPCUAProtocol(adapter)
                else:
                    print(
                        f"[WARN] Unknown protocol '{proto_name}' for device '{device_name}', skipping"
                    )
                    continue

                protocols[proto_name] = protocol
                adapters[proto_name] = adapter

            # Instantiate the device with all its protocols
            try:
                device = device_class(
                    device_id=device_id,
                    description=description,
                    protocols=protocols,
                )
            except Exception as e:
                print(f"[ERROR] Failed to instantiate device '{device_name}': {e}")
                continue

            # Store device and associated components
            self.devices[device_name] = {
                "device": device,
                "protocols": protocols,
                "adapters": adapters,
                "type": device_type,
            }

            print(
                f"[INFO] Device '{device_name}' loaded with {len(protocols)} protocol(s)"
            )

        print(f"[INFO] Total devices loaded: {len(self.devices)}")
        return True

    async def start_all(self) -> None:
        """Start all simulators."""
        self.running = True

        for name, device_data in self.devices.items():
            protocols = device_data["protocols"]
            adapters = device_data["adapters"]

            for proto_name, protocol in protocols.items():
                adapter = adapters.get(proto_name)
                try:
                    print(
                        f"[INFO] Connecting {proto_name} protocol for device '{name}'"
                    )
                    await protocol.connect()
                    if hasattr(adapter, "probe"):
                        state = await adapter.probe()
                        print(f"[INFO] Started {proto_name} on '{name}': {state}")
                    else:
                        print(f"[INFO] Started {proto_name} on '{name}'")
                except Exception as e:
                    print(
                        f"[ERROR] Failed to start {proto_name} on '{name}': {type(e).__name__}: {e}"
                    )

    async def stop_all(self) -> None:
        """Stop all simulators cleanly."""
        self.running = False

        for name, device_data in self.devices.items():
            protocols = device_data["protocols"]

            for proto_name, protocol in protocols.items():
                try:
                    await protocol.disconnect()
                    print(f"[INFO] Stopped {proto_name} on '{name}'")
                except Exception as e:
                    print(f"[ERROR] Error stopping {proto_name} on '{name}': {e}")

    async def run(self) -> None:
        """Run manager loop until interrupted."""
        await self.load_config()
        await self.start_all()

        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("[INFO] KeyboardInterrupt received, shutting down...")
            await self.stop_all()


if __name__ == "__main__":
    asyncio.run(AsyncSimulatorManager().run())
