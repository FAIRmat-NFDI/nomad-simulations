import numpy as np
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.model_system import ModelSystem


def minimal_model_system_example() -> ModelSystem:
    """Create a minimal representative ModelSystem with atomic content."""
    model_system = ModelSystem(is_representative=True)
    model_system.lattice_vectors = np.eye(3) * 5.43 * ureg.angstrom
    model_system.positions = (
        np.array([[0.0, 0.0, 0.0], [1.3575, 1.3575, 1.3575]]) * ureg.angstrom
    )
    model_system.periodic_boundary_conditions = [True, True, True]

    for symbol in ['Si', 'Si']:
        model_system.particle_states.append(AtomsState(chemical_symbol=symbol))

    return model_system
