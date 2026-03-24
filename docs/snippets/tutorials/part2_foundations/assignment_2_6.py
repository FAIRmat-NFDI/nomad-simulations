import numpy as np
from nomad import utils
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.model_system import ModelSystem

logger = utils.get_logger(__name__)

model_system = ModelSystem(is_representative=True)
model_system.lattice_vectors = np.eye(3) * 5.65 * ureg.angstrom
model_system.periodic_boundary_conditions = [True, True, True]
model_system.positions = np.array([[0, 0, 0], [2.825, 2.825, 2.825]]) * ureg.angstrom
model_system.particle_states.append(AtomsState(chemical_symbol='Ga'))
model_system.particle_states.append(AtomsState(chemical_symbol='As'))

model_system.normalize(archive=EntryArchive(), logger=logger)

assert model_system.chemical_formula is not None
assert model_system.chemical_formula.iupac == 'GaAs'
assert model_system.chemical_formula.hill == 'AsGa'
assert model_system.chemical_formula.anonymous == 'AB'
