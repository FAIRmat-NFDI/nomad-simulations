from nomad_simulations.schema_packages.general import Program, Simulation

simulation = Simulation()
program = Program(name='VASP', version='5.0.0')
simulation.program = program

assert simulation.program.name == 'VASP'
assert simulation.program.version == '5.0.0'

# Compatible scalar inputs are auto-converted to string when possible.
program.version = 5
assert program.version == '5'
