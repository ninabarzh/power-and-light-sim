# tests/test_system_state_integration.py

import pytest
from components.state.system_state import SystemState


@pytest.mark.asyncio
async def test_system_state_integration():
    state = SystemState()

    # Initially, nothing registered
    summary = await state.get_summary()
    assert summary["devices"]["total"] == 0
    assert summary["simulation"]["simulation_time"] == 0.0
    assert summary["simulation"]["update_cycles"] == 0

    # Register devices
    await state.register_device(
        device_name="turbine_plc_1",
        device_type="turbine_plc",
        device_id=1,
        protocols=["modbus"],
    )
    await state.register_device(
        device_name="substation_plc_1",
        device_type="substation_plc",
        device_id=2,
        protocols=["modbus", "iec104"],
    )

    # Check counts
    all_devices = await state.get_all_devices()
    assert len(all_devices) == 2
    turbine = await state.get_device("turbine_plc_1")
    assert turbine.device_type == "turbine_plc"
    assert turbine.online is False

    # Update device state
    await state.update_device("turbine_plc_1", online=True, memory_map={"valve": 1})
    turbine = await state.get_device("turbine_plc_1")
    assert turbine.online is True
    assert turbine.memory_map["valve"] == 1

    # Update simulation time
    await state.update_simulation_time(5.0)
    summary = await state.get_summary()
    assert summary["simulation"]["simulation_time"] == 5.0
    assert summary["simulation"]["update_cycles"] == 1

    # Query by type / protocol
    turbines = await state.get_devices_by_type("turbine_plc")
    assert len(turbines) == 1
    modbus_devices = await state.get_devices_by_protocol("modbus")
    assert len(modbus_devices) == 2
    iec104_devices = await state.get_devices_by_protocol("iec104")
    assert len(iec104_devices) == 1

    # Mark running
    await state.mark_running(True)
    summary = await state.get_summary()
    assert summary["simulation"]["running"] is True

    # Reset
    await state.reset()
    summary = await state.get_summary()
    assert summary["devices"]["total"] == 0
    assert summary["simulation"]["running"] is False
    assert summary["simulation"]["simulation_time"] == 0.0
