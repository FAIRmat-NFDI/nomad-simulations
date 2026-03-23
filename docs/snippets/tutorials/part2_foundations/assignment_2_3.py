# docs-snippet: runnable
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_method import DFT, XCFunctional

simulation = Simulation()
dft = DFT(name='DFT', type='KS', xc=XCFunctional(functional_key='PBE'))
simulation.model_method.append(dft)

assert isinstance(simulation.model_method[0], DFT)
assert simulation.model_method[0].xc.functional_key == 'PBE'
