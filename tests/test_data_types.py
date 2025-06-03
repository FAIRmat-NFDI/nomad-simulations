from unittest.mock import Mock

import numpy as np
import pytest
from nomad.metainfo import Quantity, Section
from nomad.metainfo.data_type import (
    m_float32,
    m_float64,
    m_int16,
    m_int32,
    normalize_type,
)

from nomad_simulations.schema_packages.data_types import (
    Bound,
    BoundedNumber,
)


# Test section class for serialization tests
class TestSection(Section):
    bounded_value = Quantity(
        type=BoundedNumber(dtype=float, bounds=Bound('[0,1]')),
        description='A bounded float value',
    )
    bounded_array = Quantity(
        type=BoundedNumber(dtype=int, bounds=Bound('[1,10]')),
        shape=['*'],
        description='An array of bounded integers',
    )


def setup_datatype_for_testing(datatype_instance, shape=None):
    """Helper function to set up a datatype instance for testing."""
    mock_definition = Mock()
    mock_definition.shape = shape
    mock_definition.unit = None
    mock_definition.flexible_unit = False
    datatype_instance.attach_definition(mock_definition)
    return datatype_instance


class TestBound:
    """Test the Bound class functionality."""

    @pytest.mark.parametrize(
        'range_str,test_values,should_pass',
        [
            ('[0,10]', [0, 5, 10], True),
            ('[0,10]', [-1, 11], False),
            ('(0,10)', [1, 5, 9], True),
            ('(0,10)', [0, 10], False),
            ('[5,)', [5, 100], True),
            ('[5,)', [4], False),
            ('(,10]', [-100, 0, 10], True),
            ('(,10]', [11], False),
        ],
    )
    def test_check_values(self, range_str, test_values, should_pass):
        """Test bounds checking."""
        bound = Bound(range_str)

        if should_pass:
            for value in test_values:
                bound.check(value)  # Should not raise
        else:
            for value in test_values:
                with pytest.raises(ValueError):
                    bound.check(value)

    def test_nan_behavior(self):
        """Test that NaN values pass bounds checking."""
        bound = Bound('[0,1]')

        # NaN values should pass bounds checking (due to NaN comparison behavior)
        bound.check(float('nan'))  # Should not raise
        bound.check([0.5, float('nan'), 0.8])  # Should not raise

    def test_none_behavior(self):
        """Test that None values are handled correctly."""
        bound = Bound('[0,1]')
        bound.check(None)  # Should not raise

    @pytest.mark.parametrize(
        'range_str,expected_str',
        [
            ('', '(,)'),
            ('[0,10]', '[0.0,10.0]'),
            ('(0,10)', '(0.0,10.0)'),
            ('[5,)', '[5.0,)'),
            ('(,10]', '(,10.0]'),
        ],
    )
    def test_string_representation(self, range_str, expected_str):
        """Test string representation of bounds."""
        bound = Bound(range_str)
        assert bound.get_bounds_str() == expected_str

    def test_invalid_range_format(self):
        """Test that invalid range formats raise errors."""
        with pytest.raises(ValueError, match='Invalid range format'):
            Bound('invalid')
        with pytest.raises(ValueError, match='Invalid range format'):
            Bound('[0,1,2]')


class TestBoundedNumber:
    """Test the BoundedNumber class functionality."""

    def test_basic_functionality(self):
        """Test basic BoundedNumber functionality."""
        bound = Bound('[0,10]')
        datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=int, bounds=bound), shape=None
        )

        # Valid values
        assert datatype.normalize(5) == 5
        assert datatype.normalize(0) == 0
        assert datatype.normalize(10) == 10

        # Invalid values
        with pytest.raises(ValueError):
            datatype.normalize(-1)
        with pytest.raises(ValueError):
            datatype.normalize(11)

    def test_convertible_from(self):
        """Test convertible_from delegation."""
        bound = Bound('[0,10]')
        int_datatype = BoundedNumber(dtype=int, bounds=bound)
        float_datatype = BoundedNumber(dtype=float, bounds=bound)

        # Test int datatype conversions
        assert int_datatype.convertible_from(np.int32) is True
        assert int_datatype.convertible_from(float) is False

        # Test float datatype conversions
        assert float_datatype.convertible_from(float) is True
        assert float_datatype.convertible_from(np.int32) is False

    def test_nan_handling_for_floats(self):
        """Test that float types handle NaN correctly."""
        bound = Bound('[0,1]')

        # Test scalar NaN
        scalar_datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=float, bounds=bound), shape=None
        )
        result = scalar_datatype.normalize(float('nan'))
        assert np.isnan(result)

        # Test arrays with NaN
        array_datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=float, bounds=bound), shape=['*']
        )
        result = array_datatype.normalize([0.5, float('nan'), 0.8])
        assert len(result) == 3
        assert not np.isnan(result[0])
        assert np.isnan(result[1])
        assert not np.isnan(result[2])

    def test_none_handling(self):
        """Test that None values are handled correctly."""
        bound = Bound('[0,1]')
        datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=float, bounds=bound), shape=None
        )

        # None should pass through unchanged
        result = datatype.normalize(None)
        assert result is None

    def test_array_validation(self):
        """Test validation of array structures."""
        bound = Bound('[0,10]')
        datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=int, bounds=bound), shape=['*']
        )

        # Valid array
        result = datatype.normalize([1, 5, 9])
        if isinstance(result, np.ndarray):
            assert np.array_equal(result, [1, 5, 9])
        else:
            assert result == [1, 5, 9]

        # Invalid array
        with pytest.raises(ValueError):
            datatype.normalize([1, 15, 9])

    def test_serialization_and_reconstruction(self):
        """Test that BoundedNumber can be serialized and reconstructed."""
        original = BoundedNumber(dtype=float, bounds=Bound('[0,1]'))

        # Serialize
        serialized = original.serialize_self()

        # Verify serialization format
        assert serialized['type_kind'] == 'custom'
        assert (
            'nomad_simulations.schema_packages.data_types.BoundedNumber'
            in serialized['type_data']
        )
        assert 'base_type' in serialized
        assert serialized['bounds'] == '[0.0,1.0]'

        # Reconstruct using normalize_type (like NOMAD does)
        reconstructed = normalize_type(serialized)

        # Test that reconstructed instance works
        test_datatype = setup_datatype_for_testing(reconstructed, shape=None)
        assert test_datatype.normalize(0.5) == 0.5
        with pytest.raises(ValueError):
            test_datatype.normalize(1.5)

    def test_standard_type_delegation(self):
        """Test that standard_type delegates to base type."""
        int_type = BoundedNumber(dtype=int, bounds=Bound('[0,10]'))
        float_type = BoundedNumber(dtype=float, bounds=Bound('[0,1]'))

        assert int_type.standard_type() == 'int32'
        assert float_type.standard_type() == 'float64'

    def test_uninitialized_instance(self):
        """Test behavior of uninitialized instance (for reconstruction)."""
        # This mimics what normalize_type does
        instance = BoundedNumber()

        # Should handle gracefully
        assert instance.convertible_from(int) is False
        assert instance.standard_type() == 'bounded_number'
        assert instance._dtype is None

        # Should raise error on normalize
        with pytest.raises(RuntimeError):
            instance.normalize(5)

    def test_custom_bounds_and_dtypes(self):
        """Test various combinations of bounds and dtypes."""
        test_cases = [
            # (dtype, bounds, valid_value, invalid_value)
            (m_int32(), '[1,10]', 5, 0),
            (m_float64(), '(0,1)', 0.5, 0.0),
            (m_int16(), '[0,)', 100, -1),
            (m_float32(), '(,0]', -5.0, 1.0),
        ]

        for dtype, bounds_str, valid_val, invalid_val in test_cases:
            bound = Bound(bounds_str)
            datatype = setup_datatype_for_testing(
                BoundedNumber(dtype=dtype, bounds=bound), shape=None
            )

            # Valid value should work
            assert datatype.normalize(valid_val) == valid_val

            # Invalid value should fail
            with pytest.raises(ValueError):
                datatype.normalize(invalid_val)


class TestNOMADIntegration:
    """Test integration with NOMAD's type system."""

    def test_normalize_type_string_resolution(self):
        """Test that string type references work."""
        # This tests the full NOMAD integration
        serialized_data = {
            'type_kind': 'custom',
            'type_data': 'nomad_simulations.schema_packages.data_types.BoundedNumber',
            'base_type': {'type_kind': 'python', 'type_data': 'float'},
            'bounds': '[0,1]',
        }

        # This is what NOMAD does internally
        datatype = normalize_type(serialized_data)
        assert isinstance(datatype, BoundedNumber)

        # Test it works
        test_instance = setup_datatype_for_testing(datatype, shape=None)
        assert test_instance.normalize(0.5) == 0.5
        with pytest.raises(ValueError):
            test_instance.normalize(1.5)

    def test_section_serialization_deserialization(self):
        """Test full section serialization/deserialization cycle with BoundedNumber."""
        # Create and populate a section instance
        original_section = TestSection()
        original_section.bounded_value = 0.75
        original_section.bounded_array = [1, 5, 8, 10]

        # Serialize to dict
        serialized_dict = original_section.m_to_dict()

        # Verify the serialized data contains our values
        assert serialized_dict['bounded_value'] == 0.75
        assert serialized_dict['bounded_array'] == [1, 5, 8, 10]

        # Deserialize back to a new section
        reconstructed_section = TestSection.m_from_dict(serialized_dict)

        # Verify the reconstructed section has correct values
        assert reconstructed_section.bounded_value == 0.75
        assert reconstructed_section.bounded_array == [1, 5, 8, 10]

        # Verify bounds checking still works on reconstructed section
        with pytest.raises(ValueError):
            reconstructed_section.bounded_value = 1.5  # Out of bounds

        with pytest.raises(ValueError):
            reconstructed_section.bounded_array = [1, 15, 8]  # 15 out of bounds

        # Verify valid values still work
        reconstructed_section.bounded_value = 0.25
        reconstructed_section.bounded_array = [2, 3, 4]
        assert reconstructed_section.bounded_value == 0.25
        assert reconstructed_section.bounded_array == [2, 3, 4]

    def test_elasticsearch_compatibility(self):
        """Test that bounded types map correctly for elasticsearch."""
        from nomad.metainfo.data_type import to_elastic_type

        bounded_float = BoundedNumber(dtype=float, bounds=Bound('[0,1]'))
        bounded_int = BoundedNumber(dtype=int, bounds=Bound('[0,100]'))

        # Should map the same as underlying types
        assert to_elastic_type(bounded_float, dynamic=True) == 'double'
        assert to_elastic_type(bounded_int, dynamic=True) == 'long'

    def test_mongodb_compatibility(self):
        """Test that bounded types map correctly for mongodb."""
        from mongoengine import FloatField, IntField
        from nomad.metainfo.data_type import to_mongo_type

        bounded_float = BoundedNumber(dtype=float, bounds=Bound('[0,1]'))
        bounded_int = BoundedNumber(dtype=int, bounds=Bound('[0,100]'))

        # Should map the same as underlying types
        assert to_mongo_type(bounded_float) == FloatField
        assert to_mongo_type(bounded_int) == IntField

    def test_json_schema_compatibility(self):
        """Test that bounded types map correctly for JSON schema."""
        from nomad.metainfo.data_type import to_json_schema_type

        bounded_float = BoundedNumber(dtype=float, bounds=Bound('[0,1]'))
        bounded_int = BoundedNumber(dtype=int, bounds=Bound('[0,100]'))

        # Should map the same as underlying types
        assert to_json_schema_type(bounded_float) == {'type': 'number'}
        assert to_json_schema_type(bounded_int) == {'type': 'integer'}


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_mixed_valid_invalid_values(self):
        """Test arrays with mix of valid and invalid values."""
        bound = Bound('[0,10]')
        datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=int, bounds=bound), shape=['*']
        )

        # Should fail if any value is invalid
        with pytest.raises(ValueError, match=r'All values must be in \[0\.0,10\.0\]'):
            datatype.normalize([1, 5, 15, 8])  # 15 is invalid

    def test_empty_arrays(self):
        """Test empty arrays."""
        bound = Bound('[0,10]')
        datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=int, bounds=bound), shape=['*']
        )

        # Empty arrays should be fine
        result = datatype.normalize([])
        assert len(result) == 0

    def test_infinity_bounds(self):
        """Test infinite bounds."""
        # Test positive infinity
        bound_pos = Bound('[0,)')
        datatype_pos = setup_datatype_for_testing(
            BoundedNumber(dtype=float, bounds=bound_pos), shape=None
        )

        assert datatype_pos.normalize(1e10) == 1e10  # Very large number
        with pytest.raises(ValueError):
            datatype_pos.normalize(-1)

        # Test negative infinity
        bound_neg = Bound('(,0]')
        datatype_neg = setup_datatype_for_testing(
            BoundedNumber(dtype=float, bounds=bound_neg), shape=None
        )

        assert datatype_neg.normalize(-1e10) == -1e10  # Very negative number
        with pytest.raises(ValueError):
            datatype_neg.normalize(1)

    def test_reconstruct_with_complex_bounds(self):
        """Test reconstruction with various bound types."""
        test_cases = [
            ('[0,1]', 0.5, 1.5),  # closed interval
            ('(0,1)', 0.5, 0.0),  # open interval
            ('[0,)', 100, -1),  # half-bounded
            ('', 0, 0),  # unbounded (no invalid values)
        ]

        for bounds_str, valid_val, invalid_val in test_cases:
            original = BoundedNumber(dtype=float, bounds=Bound(bounds_str))
            serialized = original.serialize_self()
            reconstructed = normalize_type(serialized)

            test_instance = setup_datatype_for_testing(reconstructed, shape=None)

            # Valid value should work
            assert test_instance.normalize(valid_val) == valid_val

            # Invalid value should fail (except for unbounded case)
            if bounds_str != '':
                with pytest.raises(ValueError):
                    test_instance.normalize(invalid_val)
