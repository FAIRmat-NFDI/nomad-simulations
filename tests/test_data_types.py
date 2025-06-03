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

    @pytest.mark.parametrize(
        'test_value,should_pass',
        [
            (float('nan'), True),  # NaN should pass
            ([0.5, float('nan'), 0.8], True),  # Array with NaN should pass
            (None, True),  # None should pass
        ],
    )
    def test_special_values(self, test_value, should_pass):
        """Test handling of special values (NaN, None)."""
        bound = Bound('[0,1]')
        if should_pass:
            bound.check(test_value)  # Should not raise
        else:
            with pytest.raises(ValueError):
                bound.check(test_value)

    @pytest.mark.parametrize(
        'range_str,expected_str,should_pass',
        [
            # Empty bounds
            ('', '(,)', True),
            # Integer bounds
            ('[0,10]', '[0,10]', True),
            ('(0,10)', '(0,10)', True),
            ('[5,)', '[5,)', True),
            ('(,10]', '(,10]', True),
            # Float bounds with different precisions
            ('[0.0,1.0]', '[0.0,1.0]', True),
            ('(0.5,1.5)', '(0.5,1.5)', True),
            ('[0.25,0.75]', '[0.25,0.75]', True),
            # High precision floats
            ('[0.123456,0.987654]', '[0.123456,0.987654]', True),
            ('(3.14159,2.71828)', '(3.14159,2.71828)', True),
            # Mixed integer and float
            ('[0,1.5]', '[0,1.5]', True),
            ('(1.0,10)', '(1.0,10)', True),
            # Negative values
            ('[-10.5,10.5]', '[-10.5,10.5]', True),
            ('(-1.23,1.23)', '(-1.23,1.23)', True),
            # Single-sided with floats
            ('[3.14,)', '[3.14,)', True),
            ('(,-2.718]', '(,-2.718]', True),
            # Scientific notation should fail
            ('[1e-3,1e3]', '', False),
            ('(1E-5,1E5)', '', False),
            ('[2.5e10,3.0E-2]', '', False),
        ],
    )
    def test_string_representation(self, range_str, expected_str, should_pass):
        """Test string representation of bounds and verify scientific notation fails."""
        if should_pass:
            bound = Bound(range_str)
            assert bound.get_bounds_str() == expected_str
        else:
            with pytest.raises(ValueError, match='Invalid range format'):
                Bound(range_str)

    @pytest.mark.parametrize(
        'invalid_range,should_raise',
        [
            ('invalid', True),
            ('[0,1,2]', True),
        ],
    )
    def test_invalid_range_format(self, invalid_range, should_raise):
        """Test that invalid range formats raise errors."""
        if should_raise:
            with pytest.raises(ValueError, match='Invalid range format'):
                Bound(invalid_range)
        else:
            Bound(invalid_range)  # Should not raise


class TestBoundedNumber:
    """Test the BoundedNumber class functionality."""

    @pytest.mark.parametrize(
        'dtype,bounds_str,test_value,should_pass',
        [
            # Basic functionality
            (int, '[0,10]', 5, True),
            (int, '[0,10]', 0, True),
            (int, '[0,10]', 10, True),
            (int, '[0,10]', -1, False),
            (int, '[0,10]', 11, False),
            # Special values
            (float, '[0,1]', float('nan'), True),
            (float, '[0,1]', None, True),
            # Array validation
            (int, '[0,10]', [1, 5, 9], True),
            (int, '[0,10]', [1, 15, 9], False),
            (int, '[0,10]', [], True),
            # Various dtypes and bounds
            (m_int32(), '[1,10]', 5, True),
            (m_int32(), '[1,10]', 0, False),
            (m_float64(), '(0,1)', 0.5, True),
            (m_float64(), '(0,1)', 0.0, False),
            (m_int16(), '[0,)', 100, True),
            (m_int16(), '[0,)', -1, False),
            (m_float32(), '(,0]', -5.0, True),
            (m_float32(), '(,0]', 1.0, False),
        ],
    )
    def test_normalization(self, dtype, bounds_str, test_value, should_pass):
        """Test value normalization with various dtypes and bounds."""
        bound = Bound(bounds_str)
        shape = ['*'] if isinstance(test_value, list) else None
        datatype = setup_datatype_for_testing(
            BoundedNumber(dtype=dtype, bounds=bound), shape=shape
        )

        if should_pass:
            result = datatype.normalize(test_value)
            if test_value is None:
                assert result is None
            elif isinstance(test_value, float) and np.isnan(test_value):
                assert np.isnan(result)
            elif isinstance(test_value, list):
                if len(test_value) == 0:
                    assert len(result) == 0
                else:
                    # Check array content
                    if isinstance(result, np.ndarray):
                        if any(np.isnan(v) for v in test_value if isinstance(v, float)):
                            # Handle NaN in arrays
                            for i, v in enumerate(test_value):
                                if isinstance(v, float) and np.isnan(v):
                                    assert np.isnan(result[i])
                                else:
                                    assert result[i] == v
                        else:
                            assert np.array_equal(result, test_value)
                    else:
                        assert result == test_value
            else:
                assert result == test_value
        else:
            with pytest.raises(ValueError):
                datatype.normalize(test_value)

    @pytest.mark.parametrize(
        'dtype,other_type,should_convert',
        [
            (int, np.int32, True),
            (int, float, False),
            (float, float, True),
            (float, np.int32, False),
        ],
    )
    def test_convertible_from(self, dtype, other_type, should_convert):
        """Test convertible_from delegation."""
        bound = Bound('[0,10]')
        datatype = BoundedNumber(dtype=dtype, bounds=bound)
        assert datatype.convertible_from(other_type) is should_convert

    @pytest.mark.parametrize(
        'dtype,expected_type',
        [
            (int, 'int32'),
            (float, 'float64'),
        ],
    )
    def test_standard_type_delegation(self, dtype, expected_type):
        """Test that standard_type delegates to base type."""
        datatype = BoundedNumber(dtype=dtype, bounds=Bound('[0,1]'))
        assert datatype.standard_type() == expected_type

    def test_serialization_and_reconstruction(self):
        """Test that BoundedNumber can be serialized and reconstructed."""
        original = BoundedNumber(dtype=float, bounds=Bound('[0,1]'))

        serialized = original.serialize_self()

        assert serialized['type_kind'] == 'custom'
        assert (
            'nomad_simulations.schema_packages.data_types.BoundedNumber'
            in serialized['type_data']
        )
        assert 'base_type' in serialized
        assert serialized['bounds'] == '[0,1]'

        reconstructed = normalize_type(serialized)

        test_datatype = setup_datatype_for_testing(reconstructed, shape=None)
        assert test_datatype.normalize(0.5) == 0.5
        with pytest.raises(ValueError):
            test_datatype.normalize(1.5)

    def test_uninitialized_instance(self):
        """Test behavior of uninitialized instance (for reconstruction)."""
        instance = BoundedNumber()

        # Should handle gracefully
        assert instance.convertible_from(int) is False
        assert instance.standard_type() == 'bounded_number'
        assert instance._dtype is None

        # Should raise error on normalize
        with pytest.raises(RuntimeError):
            instance.normalize(5)


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

    @pytest.mark.parametrize(
        'section_data,should_pass,description',
        [
            # Valid deserialization
            (
                {'bounded_value': 0.75, 'bounded_array': [1, 5, 8, 10]},
                True,
                'valid data',
            ),
            # Invalid deserialization
            (
                {'bounded_value': 1.5, 'bounded_array': [1, 15, 8]},
                False,
                'invalid data',
            ),
        ],
    )
    def test_section_serialization_deserialization(
        self, section_data, should_pass, description
    ):
        """Test full section serialization/deserialization cycle with BoundedNumber."""
        if should_pass:
            # Test successful round-trip
            original_section = TestSection()
            original_section.bounded_value = section_data['bounded_value']
            original_section.bounded_array = section_data['bounded_array']

            # Serialize to dict
            serialized_dict = original_section.m_to_dict()

            # Verify the serialized data contains our values
            assert serialized_dict['bounded_value'] == section_data['bounded_value']
            assert serialized_dict['bounded_array'] == section_data['bounded_array']

            # Deserialize back to a new section
            reconstructed_section = TestSection.m_from_dict(serialized_dict)

            # Verify the reconstructed section has correct values
            assert reconstructed_section.bounded_value == section_data['bounded_value']
            assert reconstructed_section.bounded_array == section_data['bounded_array']

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
        else:
            # Test that invalid data fails during deserialization
            with pytest.raises(ValueError):
                TestSection.m_from_dict(section_data)

    @pytest.mark.parametrize(
        'compatibility_type,dtype,bounds_str,expected',
        [
            ('elasticsearch', float, '[0,1]', 'double'),
            ('elasticsearch', int, '[0,100]', 'long'),
            ('mongodb_float', float, '[0,1]', 'FloatField'),
            ('mongodb_int', int, '[0,100]', 'IntField'),
            ('json_schema_float', float, '[0,1]', {'type': 'number'}),
            ('json_schema_int', int, '[0,100]', {'type': 'integer'}),
        ],
    )
    def test_external_system_compatibility(
        self, compatibility_type, dtype, bounds_str, expected
    ):
        """Test that bounded types map correctly for external systems."""
        bounded_type = BoundedNumber(dtype=dtype, bounds=Bound(bounds_str))

        if compatibility_type == 'elasticsearch':
            from nomad.metainfo.data_type import to_elastic_type

            assert to_elastic_type(bounded_type, dynamic=True) == expected
        elif compatibility_type.startswith('mongodb'):
            from mongoengine import FloatField, IntField
            from nomad.metainfo.data_type import to_mongo_type

            expected_class = FloatField if expected == 'FloatField' else IntField
            assert to_mongo_type(bounded_type) == expected_class
        elif compatibility_type.startswith('json_schema'):
            from nomad.metainfo.data_type import to_json_schema_type

            assert to_json_schema_type(bounded_type) == expected


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.parametrize(
        'bounds_str,test_values,should_pass,error_match',
        [
            # Mixed valid/invalid values
            ('[0,10]', [1, 5, 15, 8], False, r'All values must be in \[0,10\]'),
            # Empty arrays
            ('[0,10]', [], True, None),
            # Infinity bounds
            ('[0,)', [1e10], True, None),
            ('[0,)', [-1], False, None),
            ('(,0]', [-1e10], True, None),
            ('(,0]', [1], False, None),
        ],
    )
    def test_edge_case_arrays(self, bounds_str, test_values, should_pass, error_match):
        """Test edge cases with array values."""
        bound = Bound(bounds_str)
        datatype = setup_datatype_for_testing(
            BoundedNumber(
                dtype=float if any(isinstance(v, float) for v in test_values) else int,
                bounds=bound,
            ),
            shape=['*'],
        )

        if should_pass:
            result = datatype.normalize(test_values)
            if len(test_values) == 0:
                assert len(result) == 0
            else:
                # For large numbers, just check they're processed
                assert len(result) == len(test_values)
        else:
            if error_match:
                with pytest.raises(ValueError, match=error_match):
                    datatype.normalize(test_values)
            else:
                with pytest.raises(ValueError):
                    datatype.normalize(test_values)

    @pytest.mark.parametrize(
        'bounds_str,valid_val,invalid_val',
        [
            ('[0,1]', 0.5, 1.5),  # closed interval
            ('(0,1)', 0.5, 0.0),  # open interval
            ('[0,)', 100, -1),  # half-bounded
            ('', 0, None),  # unbounded (no invalid values)
        ],
    )
    def test_reconstruct_with_complex_bounds(self, bounds_str, valid_val, invalid_val):
        """Test reconstruction with various bound types."""
        original = BoundedNumber(dtype=float, bounds=Bound(bounds_str))
        serialized = original.serialize_self()
        reconstructed = normalize_type(serialized)

        test_instance = setup_datatype_for_testing(reconstructed, shape=None)

        # Valid value should work
        assert test_instance.normalize(valid_val) == valid_val

        # Invalid value should fail (except for unbounded case)
        if bounds_str != '' and invalid_val is not None:
            with pytest.raises(ValueError):
                test_instance.normalize(invalid_val)
