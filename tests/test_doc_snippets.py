import numpy as np

from docs.snippets.model_system.alternative_representation_pattern import (
    alternative_representation_example,
)
from docs.snippets.model_system.minimal_parser_pattern import (
    minimal_model_system_example,
)


def test_minimal_model_system_example():
    model_system = minimal_model_system_example()
    assert model_system.is_representative is True
    assert len(model_system.particle_states) == 2
    assert model_system.periodic_boundary_conditions == [True, True, True]
    assert np.asarray(model_system.lattice_vectors.magnitude).shape == (3, 3)
    assert np.asarray(model_system.positions.magnitude).shape == (2, 3)


def test_alternative_representation_example():
    model_system = alternative_representation_example()
    assert len(model_system.representations) == 1
    rep = model_system.representations[0]
    assert rep.name == 'primitive'
    assert rep.crystal_cell_type == 'primitive'
    assert np.asarray(rep.lattice_vectors.magnitude).shape == (3, 3)

