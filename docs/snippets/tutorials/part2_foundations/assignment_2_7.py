import numpy as np
from nomad import utils
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_method import DFT
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.numerical_settings import SelfConsistency
from nomad_simulations.schema_packages.outputs import Outputs, SCFSteps
from nomad_simulations.schema_packages.properties import TotalEnergy

logger = utils.get_logger(__name__)

simulation = Simulation()

model_system = ModelSystem(is_representative=True)
model_system.lattice_vectors = np.eye(3) * 5.0 * ureg.angstrom
model_system.periodic_boundary_conditions = [True, True, True]
model_system.positions = np.array([[0, 0, 0], [1.25, 1.25, 1.25]]) * ureg.angstrom
model_system.particle_states.append(AtomsState(chemical_symbol='Si'))
model_system.particle_states.append(AtomsState(chemical_symbol='Si'))
simulation.model_system.append(model_system)

method = DFT(
    name='DFT',
    type='KS',
    numerical_settings=[SelfConsistency(threshold_change=1e-6 * ureg.joule)],
)
simulation.model_method.append(method)

outputs = Outputs(scf_steps=SCFSteps())
for value in [1.0, 1.5, 2.0, 2.1, 2.101]:
    outputs.total_energies.append(TotalEnergy(value=value * ureg.eV))
simulation.outputs.append(outputs)

outputs.normalize(archive=EntryArchive(), logger=logger)

assert outputs.model_system_ref is simulation.model_system[0]
assert outputs.model_method_ref is simulation.model_method[0]
assert outputs.scf_steps is not None
assert outputs.scf_steps.delta_energies_total is not None
assert len(outputs.scf_steps.delta_energies_total) == 4
first_delta_joule = outputs.scf_steps.delta_energies_total[0].to('joule').magnitude
assert np.isclose(first_delta_joule, (0.5 * ureg.eV).to('joule').magnitude)
