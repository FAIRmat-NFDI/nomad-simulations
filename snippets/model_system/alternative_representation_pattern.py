import numpy as np
from nomad.units import ureg

from nomad_simulations.schema_packages.model_system import (
    AlternativeRepresentation,
    ModelSystem,
)


def alternative_representation_example() -> ModelSystem:
    """Attach a primitive representation to a ModelSystem."""
    model_system = ModelSystem()
    model_system.lattice_vectors = np.eye(3) * 5.43 * ureg.angstrom
    model_system.positions = (
        np.array([[0.0, 0.0, 0.0], [1.3575, 1.3575, 1.3575]]) * ureg.angstrom
    )

    model_system.representations.append(
        AlternativeRepresentation(
            name='primitive',
            crystal_cell_type='primitive',
            lattice_vectors=np.eye(3) * 2.715 * ureg.angstrom,
        )
    )

    return model_system
