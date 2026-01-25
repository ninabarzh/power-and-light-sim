# tests/test_turbine_physics_sim.py
import asyncio

from components.physics.turbine_physics import TurbinePhysics


async def run_sim():
    sim = TurbinePhysics()
    sim.set_governor_enabled(True)
    sim.set_speed_setpoint(3600)

    await sim.start()
    await asyncio.sleep(40)  # simulate 40 seconds
    await sim.stop()

    state = sim.get_state()
    print(f"Shaft speed: {state.shaft_speed_rpm}")
    print(f"Power output: {state.power_output_mw}")
    print(f"Damage: {state.damage_level}")


if __name__ == "__main__":
    asyncio.run(run_sim())
