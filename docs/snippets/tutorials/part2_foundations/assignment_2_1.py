# docs-snippet: runnable
from nomad.units import ureg

from nomad_simulations.schema_packages.general import Simulation

simulation = Simulation()
simulation.cpu1_start = 0 * ureg.second
simulation.cpu1_end = 30 * ureg.second + 24 * ureg.minute

elapsed_seconds = (simulation.cpu1_end - simulation.cpu1_start).to('second').magnitude
elapsed_hours = (simulation.cpu1_end - simulation.cpu1_start).to('hour').magnitude

assert elapsed_seconds == 1470
assert round(elapsed_hours, 6) == round(1470 / 3600, 6)
