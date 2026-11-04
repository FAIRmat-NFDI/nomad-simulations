from nomad_simulations.schema_packages.general import Program, Simulation


def build_simulation_with_program() -> Simulation:
    simulation = Simulation()
    simulation.program = Program(name='SUPERCODE', version='7.0')
    return simulation
