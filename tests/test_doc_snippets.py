import numpy as np

from docs.snippets.data_types.basic_usage import build_valid_section
from docs.snippets.data_types.error_handling import bounded_error_message
from docs.snippets.data_types.factory_masks import factory_bounds_map
from docs.snippets.data_types.schema_context_roundtrip import schema_context_roundtrip
from docs.snippets.data_types.standalone_type_roundtrip import (
    standalone_type_roundtrip,
)
from docs.snippets.data_types.validation_behavior import demo_validation_behavior
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


def test_data_types_basic_usage():
    section = build_valid_section()
    assert section.count == 3
    assert section.probability == 0.5
    assert section.energies == [0.1, 1.2, 3.4]


def test_data_types_factory_masks():
    bounds = factory_bounds_map()
    assert bounds['positive_int'] == '[0,)'
    assert bounds['strictly_positive_int'] == '[1,)'
    assert bounds['positive_float'] == '[0,)'
    assert bounds['strictly_positive_float'] == '(0,)'
    assert bounds['unit_float'] == '[0,1]'


def test_data_types_validation_behavior():
    valid_values, error_message = demo_validation_behavior()
    assert valid_values == [0.0, 0.5, 1.0]
    assert 'All values must be in [0.0,1.0]' in error_message


def test_data_types_schema_context_roundtrip():
    value = schema_context_roundtrip()
    assert value == 0.8


def test_data_types_standalone_roundtrip_behavior():
    original_class, reconstructed_class = standalone_type_roundtrip()
    assert original_class == 'm_float_bounded'
    # Current expected behavior: reconstructed type loses bound wrapper.
    assert reconstructed_class != 'm_float_bounded'


def test_data_types_error_message():
    message = bounded_error_message()
    assert 'All values must be in [0.0,1.0]' in message
