# tests/integration/test_network_protocol_integration.py

import pytest

from components.network.network_simulator import NetworkSimulator
from components.network.protocol_simulator import ProtocolSimulator
from components.state.system_state import SystemState
from components.time.simulation_time import SimulationTime


# Dummy protocol handler for testing
class DummyHandler:
    def __init__(self):
        self.served = False

    async def serve(self, _reader, writer):
        self.served = True
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_network_protocol_integration(tmp_path):
    # -------------------------
    # Setup system state
    # -------------------------
    system_state = SystemState()
    sim_time = SimulationTime()

    # Step manually (we'll just use delta updates)
    await sim_time.reset()

    # -------------------------
    # Register devices
    # -------------------------
    await system_state.register_device(
        device_name="turbine_plc_1",
        device_type="turbine_plc",
        device_id=1,
        protocols=["modbus"],
    )
    await system_state.register_device(
        device_name="scada_server_1",
        device_type="scada_server",
        device_id=2,
        protocols=["modbus"],
    )

    # -------------------------
    # Setup network simulator
    # -------------------------
    # Create a temporary network config file
    network_yaml = tmp_path / "network.yml"
    network_yaml.write_text("""
networks:
  - name: corporate_network
connections:
  corporate_network:
    - turbine_plc_1
    - scada_server_1
""")

    network_sim = NetworkSimulator(config_path=str(network_yaml))
    await network_sim.load()

    # -------------------------
    # Setup protocol simulator
    # -------------------------
    protocol_sim = ProtocolSimulator(network=network_sim)

    # Register listeners
    await protocol_sim.register(
        node="turbine_plc_1",
        network="corporate_network",
        port=15020,
        protocol="modbus",
        handler_factory=DummyHandler,
    )
    await protocol_sim.register(
        node="scada_server_1",
        network="corporate_network",
        port=15022,
        protocol="modbus",
        handler_factory=DummyHandler,
    )

    # -------------------------
    # Start protocol listeners
    # -------------------------
    await protocol_sim.start()

    # -------------------------
    # Test network reachability
    # -------------------------
    can_reach_turbine = await network_sim.can_reach(
        "corporate_network", "turbine_plc_1", "modbus", 15020
    )
    can_reach_scada = await network_sim.can_reach(
        "corporate_network", "scada_server_1", "modbus", 15022
    )

    assert can_reach_turbine is True
    assert can_reach_scada is True

    # -------------------------
    # Update state
    # -------------------------
    await system_state.update_device("turbine_plc_1", online=True)
    await system_state.update_device("scada_server_1", online=True)
    await system_state.update_simulation_time(1.0)

    summary = await system_state.get_summary()
    assert summary["devices"]["total"] == 2
    assert summary["devices"]["online"] == 2
    assert summary["simulation"]["simulation_time"] == 1.0

    # -------------------------
    # Cleanup
    # -------------------------
    await protocol_sim.stop()
