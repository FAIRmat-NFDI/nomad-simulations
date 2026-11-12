import numpy as np
from nomad import utils
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.model_system import ModelSystem

logger = utils.get_logger(__name__)

# Pattern based on tests/test_model_system.py normalization behavior.
model_system = ModelSystem(is_representative=True)
model_system.lattice_vectors = np.eye(3) * 5.43 * ureg.angstrom
model_system.periodic_boundary_conditions = [True, True, True]
model_system.positions = (
    np.array([[0.0, 0.0, 0.0], [1.3575, 1.3575, 1.3575]]) * ureg.angstrom
)
model_system.particle_states.append(AtomsState(chemical_symbol='Si'))
model_system.particle_states.append(AtomsState(chemical_symbol='Si'))

model_system.normalize(EntryArchive(), logger)

assert model_system.type == 'bulk'
assert model_system.chemical_formula is not None
assert model_system.chemical_formula.reduced == 'Si'
