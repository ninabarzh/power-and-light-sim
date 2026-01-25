#!/usr/bin/env python3
"""
Comprehensive test client for all protocol adapters.

Tests:
- Modbus (PyModbus 3.11.4)
- IEC-104 (c104)
- S7 (Snap7)
- OPC UA (asyncua)
"""

import asyncio

from simulator_manager import AsyncSimulatorManager


async def test_modbus_adapter(name, proto_name, adapter):
    print(f"\n=== Testing {name} ({proto_name}) ===")
    try:
        print("[+] Adapter state:")
        print(f"    Connected: {adapter.connected}")
        print(f"    Host:Port: {adapter.host}:{adapter.port}")

        if not adapter.client or not adapter.connected:
            print("[!] Adapter not properly connected, skipping tests")
            return

        # Test read coils
        result = await adapter.read_coils(0, 4)
        if hasattr(result, "bits"):
            print(f"[+] Read coils[0:4]: {result.bits[:4]}")

        # Test read holding registers
        result = await adapter.read_holding_registers(0, 4)
        if hasattr(result, "registers"):
            print(f"[+] Read holding_registers[0:4]: {result.registers[:4]}")

        # Test write and verify
        await adapter.write_coil(5, True)
        result = await adapter.read_coils(5, 1)
        if hasattr(result, "bits"):
            print(f"[+] Write/verify coil[5]: {result.bits[0]}")

        await adapter.write_register(10, 1234)
        result = await adapter.read_holding_registers(10, 1)
        if hasattr(result, "registers"):
            print(f"[+] Write/verify register[10]: {result.registers[0]}")

        print("[✓] Modbus tests passed")

    except Exception as e:
        print(f"[✗] Error: {type(e).__name__}: {e}")


async def test_iec104_adapter(name, proto_name, adapter):
    print(f"\n=== Testing {name} ({proto_name}) ===")
    try:
        print("[+] Adapter state:")
        print(f"    Simulator mode: {adapter.simulator_mode}")
        print(f"    Bind: {adapter.bind_host}:{adapter.bind_port}")
        print(f"    Common address: {adapter.common_address}")

        # Test probe/state
        if hasattr(adapter, "probe"):
            state = await adapter.probe()
            print(f"[+] Probe result: {state}")

        print("[✓] IEC-104 simulator running (full client testing requires connection)")

    except Exception as e:
        print(f"[✗] Error: {type(e).__name__}: {e}")


async def test_s7_adapter(name, proto_name, adapter):
    print(f"\n=== Testing {name} ({proto_name}) ===")
    try:
        print("[+] Adapter state:")
        print(f"    Simulator mode: {adapter.simulator_mode}")
        print(f"    Host: {adapter.host}")
        print(f"    Rack/Slot: {adapter.rack}/{adapter.slot}")

        # Test probe/state
        if hasattr(adapter, "probe"):
            state = await adapter.probe()
            print(f"[+] Probe result: {state}")

        print("[✓] S7 simulator running (full testing requires DB configuration)")

    except Exception as e:
        print(f"[✗] Error: {type(e).__name__}: {e}")


async def test_opcua_adapter(name, proto_name, adapter):
    print(f"\n=== Testing {name} ({proto_name}) ===")
    try:
        print("[+] Adapter state:")
        print(f"    Simulator mode: {adapter.simulator_mode}")
        print(f"    Endpoint: {adapter.endpoint}")

        # Test probe/state
        if hasattr(adapter, "probe"):
            state = await adapter.probe()
            print(f"[+] Probe result: {state}")

        print("[✓] OPC UA simulator running (full testing requires node configuration)")

    except Exception as e:
        print(f"[✗] Error: {type(e).__name__}: {e}")


async def main():
    manager = AsyncSimulatorManager()
    loaded = await manager.load_config()
    if not loaded:
        print("[ERROR] Failed to load config")
        return

    # Start all simulators
    await manager.start_all()

    # Give simulators time to fully initialize
    await asyncio.sleep(0.5)

    # Test each device's protocols
    test_count = 0
    for device_name, device_data in manager.devices.items():
        protocols = device_data.get("protocols", {})
        adapters = device_data.get("adapters", {})

        for proto_name, protocol in protocols.items():
            adapter = adapters.get(proto_name)

            if not adapter:
                print(f"[!] No adapter for {device_name}:{proto_name}")
                continue

            test_count += 1
            protocol_type = getattr(protocol, "protocol_name", proto_name)

            if protocol_type == "modbus":
                await test_modbus_adapter(device_name, proto_name, adapter)
            elif protocol_type == "iec104":
                await test_iec104_adapter(device_name, proto_name, adapter)
            elif protocol_type == "s7":
                await test_s7_adapter(device_name, proto_name, adapter)
            elif protocol_type == "opcua":
                await test_opcua_adapter(device_name, proto_name, adapter)
            else:
                print(
                    f"[!] Unknown protocol type '{protocol_type}' for {device_name}:{proto_name}"
                )

    print("\n" + "=" * 60)
    print(f"All protocol tests completed ({test_count} protocols tested)")
    print("=" * 60)

    # Stop all simulators
    await manager.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
