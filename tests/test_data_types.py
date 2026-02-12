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
from nomad.units import ureg

from nomad_simulations.schema_packages.data_types import (
    Bound,
    m_float_bounded,
    m_int_bounded,
)


# Test section class for serialization tests
class TestSection(Section):
    bounded_value = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0,1]')),
        description='A bounded float value',
    )
    bounded_array = Quantity(
        type=m_int_bounded(dtype=int, bound=Bound('[1,10]')),
        shape=['*'],
        description='An array of bounded integers',
    )


# Unit test section class for serialization tests
class TestUnitSerializationSection(Section):
    bounded_quantity = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0,10]')), unit='joule'
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
            assert str(bound) == expected_str
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


class TestBoundedTypes:
    """Test the m_int_bounded and m_float_bounded class functionality."""

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

        # Extract the underlying dtype if it's a datatype instance
        if hasattr(dtype, '_dtype'):
            underlying_dtype = dtype._dtype
        else:
            underlying_dtype = dtype

        # Choose appropriate bounded type based on dtype
        dtype_name = (
            str(type(dtype).__name__) if not isinstance(dtype, type) else dtype.__name__
        )
        if underlying_dtype is int or 'int' in dtype_name.lower():
            bounded_type = m_int_bounded(dtype=underlying_dtype, bound=bound)
        else:
            bounded_type = m_float_bounded(dtype=underlying_dtype, bound=bound)

        datatype = setup_datatype_for_testing(bounded_type, shape=shape)

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
        'bounded_class,dtype,other_type,should_convert',
        [
            (m_int_bounded, int, np.int32, True),
            (m_int_bounded, int, float, False),
            (m_float_bounded, float, float, True),
            (m_float_bounded, float, np.int32, False),
            (m_int_bounded, np.int32, np.int16, True),
            (m_float_bounded, np.float64, np.float32, True),
        ],
    )
    def test_convertible_from(self, bounded_class, dtype, other_type, should_convert):
        """Test convertible_from for bounded types."""
        bound = Bound('[0,10]')
        datatype = bounded_class(dtype=dtype, bound=bound)
        assert datatype.convertible_from(other_type) is should_convert

    @pytest.mark.parametrize(
        'bounded_class,dtype,expected_type',
        [
            (m_int_bounded, int, 'int'),
            (m_float_bounded, float, 'float'),
        ],
    )
    def test_standard_type_delegation(self, bounded_class, dtype, expected_type):
        """Test that standard_type returns correct type."""
        datatype = bounded_class(dtype=dtype, bound=Bound('[0,1]'))
        assert datatype.standard_type() == expected_type

    def test_serialization_and_reconstruction(self):
        """Test that bounded types can be serialized and reconstructed."""
        original = m_float_bounded(dtype=float, bound=Bound('[0,1]'))
        serialized = original.serialize_self()

        assert serialized['type_kind'] == 'python'
        assert serialized['type_bound'] == '[0,1]'

        reconstructed = normalize_type(serialized)
        test_datatype = setup_datatype_for_testing(reconstructed, shape=None)

        assert test_datatype.normalize(0.5) == 0.5
        assert test_datatype.normalize(1.5) == 1.5

    def test_basic_functionality(self):
        """Test basic functionality of bounded types."""
        int_bounded = m_int_bounded(dtype=int, bound=Bound('[0,10]'))
        float_bounded = m_float_bounded(dtype=float, bound=Bound('[0.0,1.0]'))

        # Test basic functionality
        assert int_bounded.standard_type() == 'int'
        assert float_bounded.standard_type() == 'float'

        # Test convertibility
        assert int_bounded.convertible_from(np.int32) is True
        assert float_bounded.convertible_from(np.float32) is True


class TestNOMADIntegration:
    """Test integration with NOMAD's type system."""

    def test_normalize_type_string_resolution(self):
        """Test that string type references work."""
        # This tests the full NOMAD integration
        serialized_data = {
            'type_kind': 'custom',
            'type_data': 'nomad_simulations.schema_packages.data_types.m_float_bounded',
            'type_bound': '[0,1]',
        }

        # This is what NOMAD does internally
        datatype = normalize_type(serialized_data)
        assert isinstance(datatype, m_float_bounded)

        # Test it works
        test_instance = setup_datatype_for_testing(datatype, shape=None)
        assert test_instance.normalize(0.5) == 0.5
        with pytest.raises(ValueError):
            test_instance.normalize(1.5)

    @pytest.mark.parametrize(
        'section_data,should_pass',
        [
            (
                {'bounded_value': 0.75, 'bounded_array': [1, 5, 8, 10]},
                True,
            ),
            (
                {'bounded_value': 1.5, 'bounded_array': [1, 15, 8]},
                False,
            ),
        ],
    )
    def test_section_serialization_deserialization(self, section_data, should_pass):
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
        # Extract the underlying dtype if it's a datatype instance
        if hasattr(dtype, '_dtype'):
            underlying_dtype = dtype._dtype
        else:
            underlying_dtype = dtype

        if underlying_dtype is int:
            bounded_type = m_int_bounded(
                dtype=underlying_dtype, bound=Bound(bounds_str)
            )
        else:
            bounded_type = m_float_bounded(
                dtype=underlying_dtype, bound=Bound(bounds_str)
            )

        if compatibility_type == 'elasticsearch':
            try:
                from nomad.metainfo.data_type import to_elastic_type

                assert to_elastic_type(bounded_type, dynamic=True) == expected
            except ImportError:
                pytest.skip('to_elastic_type not available')
        elif compatibility_type.startswith('mongodb'):
            try:
                from mongoengine import FloatField, IntField
                from nomad.metainfo.data_type import to_mongo_type

                expected_class = FloatField if expected == 'FloatField' else IntField
                assert to_mongo_type(bounded_type) == expected_class
            except ImportError:
                pytest.skip('mongoengine or to_mongo_type not available')
        elif compatibility_type.startswith('json_schema'):
            try:
                from nomad.metainfo.data_type import to_json_schema_type

                assert to_json_schema_type(bounded_type) == expected
            except ImportError:
                pytest.skip('to_json_schema_type not available')


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
        dtype = float if any(isinstance(v, float) for v in test_values) else int
        if dtype is int:
            bounded_type = m_int_bounded(dtype=dtype, bound=bound)
        else:
            bounded_type = m_float_bounded(dtype=dtype, bound=bound)
        datatype = setup_datatype_for_testing(bounded_type, shape=['*'])

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
        original = m_float_bounded(dtype=float, bound=Bound(bounds_str))
        serialized = original.serialize_self()
        reconstructed = normalize_type(serialized)

        test_instance = setup_datatype_for_testing(reconstructed, shape=None)

        # Valid value should work
        assert test_instance.normalize(valid_val) == valid_val

        # Note: bounds are lost during reconstruction, so invalid values should also pass
        if invalid_val is not None:
            assert test_instance.normalize(invalid_val) == invalid_val


class TestUnitHandling:
    """Test unit preservation and handling with BoundedNumber."""

    @pytest.mark.parametrize('dtype', [float, int, m_float64(), m_int32()])
    @pytest.mark.parametrize('bounds_str', ['[0,10]', '(0,1)', '[0,)'])
    @pytest.mark.parametrize('unit_str', ['joule', 'meter', 'second'])
    def test_unit_preservation_scalar(self, dtype, bounds_str, unit_str):
        """Test that units are preserved for scalar values."""

        # Extract the underlying dtype if it's a datatype instance
        if hasattr(dtype, '_dtype'):
            underlying_dtype = dtype._dtype
        else:
            underlying_dtype = dtype

        dtype_name = (
            str(type(dtype).__name__) if not isinstance(dtype, type) else dtype.__name__
        )
        if underlying_dtype is int or 'int' in dtype_name.lower():

            class TestUnitSection(Section):
                bounded_quantity = Quantity(
                    type=m_int_bounded(dtype=underlying_dtype, bound=Bound(bounds_str)),
                    unit=unit_str,
                )
        else:

            class TestUnitSection(Section):
                bounded_quantity = Quantity(
                    type=m_float_bounded(
                        dtype=underlying_dtype, bound=Bound(bounds_str)
                    ),
                    unit=unit_str,
                )

        section = TestUnitSection()

        # Test with valid value within bounds, compatible with dtype
        if bounds_str == '[0,10]':
            test_value = 5.0
        elif bounds_str == '(0,1)':
            if 'int' in str(dtype).lower() or (
                isinstance(dtype, type) and dtype is int
            ):
                pytest.skip('Cannot convert 0.5 to integer type')
            test_value = 0.5
        elif bounds_str == '[0,)':
            test_value = 100.0

        # Assign value with unit
        section.bounded_quantity = test_value * getattr(ureg, unit_str)

        # Check that value is a Pint quantity with correct unit
        assert hasattr(section.bounded_quantity, 'magnitude')
        assert hasattr(section.bounded_quantity, 'units')
        assert section.bounded_quantity.magnitude == test_value
        assert str(section.bounded_quantity.units) == unit_str

    @pytest.mark.parametrize('dtype', [float, int])
    @pytest.mark.parametrize('unit_str', ['joule', 'meter'])
    def test_unit_preservation_array(self, dtype, unit_str):
        """Test that units are preserved for array values."""

        if dtype is int:

            class TestUnitSection(Section):
                bounded_array = Quantity(
                    type=m_int_bounded(dtype=dtype, bound=Bound('[0,10]')),
                    shape=['*'],
                    unit=unit_str,
                )
        else:

            class TestUnitSection(Section):
                bounded_array = Quantity(
                    type=m_float_bounded(dtype=dtype, bound=Bound('[0,10]')),
                    shape=['*'],
                    unit=unit_str,
                )

        section = TestUnitSection()
        test_values = [1.0, 5.0, 9.0]

        # Assign array with unit
        section.bounded_array = test_values * getattr(ureg, unit_str)

        # Check that value is a Pint quantity with correct unit
        assert hasattr(section.bounded_array, 'magnitude')
        assert hasattr(section.bounded_array, 'units')
        assert np.allclose(section.bounded_array.magnitude, test_values)
        assert str(section.bounded_array.units) == unit_str

    @pytest.mark.parametrize('dtype', [float, int])
    @pytest.mark.parametrize(
        'unit_conversion,source_value,bounds_str',
        [
            (('kilojoule', 'joule', 1000.0), 0.005, '[0,10]'),  # 0.005 kJ = 5 J
            (('centimeter', 'meter', 0.01), 500.0, '[0,1000]'),  # 500 cm = 5 m
            (('millisecond', 'second', 0.001), 5000.0, '[0,10000]'),  # 5000 ms = 5 s
        ],
    )
    def test_unit_conversion(self, dtype, unit_conversion, source_value, bounds_str):
        """Test that unit conversion works correctly with bounds checking."""
        from_unit, to_unit, conversion_factor = unit_conversion

        # Skip int tests for non-integer source values
        if dtype is int and not source_value.is_integer():
            pytest.skip('Cannot convert non-integer to int type')

        class TestUnitSection(Section):
            if dtype is int:
                bounded_quantity = Quantity(
                    type=m_int_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit=to_unit,  # Target unit
                )
            else:
                bounded_quantity = Quantity(
                    type=m_float_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit=to_unit,  # Target unit
                )

        section = TestUnitSection()

        # Assign value in source unit (should be converted to target unit)
        section.bounded_quantity = source_value * getattr(ureg, from_unit)

        # Check that value was converted and bounds still work
        assert hasattr(section.bounded_quantity, 'magnitude')
        expected_magnitude = source_value * conversion_factor
        assert np.isclose(section.bounded_quantity.magnitude, expected_magnitude)
        assert str(section.bounded_quantity.units) == to_unit

    @pytest.mark.parametrize('dtype', [float, int])
    @pytest.mark.parametrize(
        'bounds_str,valid_value,invalid_value',
        [('[0,10]', 5.0, 15.0), ('(0,1)', 0.5, 1.5), ('[0,)', 100.0, -1.0)],
    )
    def test_bounds_checking_with_units(
        self, dtype, bounds_str, valid_value, invalid_value
    ):
        """Test that bounds checking works correctly with unit quantities."""

        # Skip integer types for (0,1) bounds since 0.5 can't convert to int
        if dtype is int and bounds_str == '(0,1)':
            pytest.skip('Cannot convert 0.5 to integer type')

        class TestUnitSection(Section):
            if dtype is int:
                bounded_quantity = Quantity(
                    type=m_int_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit='joule',
                )
            else:
                bounded_quantity = Quantity(
                    type=m_float_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit='joule',
                )

        section = TestUnitSection()

        # Valid value should work
        section.bounded_quantity = valid_value * ureg.joule
        assert section.bounded_quantity.magnitude == valid_value

        # Invalid value should fail
        with pytest.raises(ValueError, match=r'All values must be in'):
            section.bounded_quantity = invalid_value * ureg.joule

    def test_unit_stripping_during_normalization(self):
        """Test that units are properly handled during the normalization process."""
        bounded_type = m_float_bounded(dtype=float, bound=Bound('[0,10]'))
        bounded_type = setup_datatype_for_testing(bounded_type, shape=None)
        quantity_value = 5.0 * ureg.joule

        # Direct normalization should extract magnitude
        normalized = bounded_type.normalize(quantity_value)
        assert normalized == 5.0
        assert not hasattr(normalized, 'magnitude')  # Plain float

        # in a Quantity with unit, NOMAD should wrap it back
        class TestUnitSection(Section):
            test_quantity = Quantity(
                type=m_float_bounded(dtype=float, bound=Bound('[0,10]')), unit='joule'
            )

        section = TestUnitSection()
        section.test_quantity = quantity_value

        # Should be wrapped back as a quantity
        assert hasattr(section.test_quantity, 'magnitude')
        assert section.test_quantity.magnitude == 5.0

    def test_serialization_with_units(self):
        """Test that serialization works correctly with unit quantities."""

        # Create and populate section using module-level class
        original_section = TestUnitSerializationSection()
        test_value = 5.0
        original_section.bounded_quantity = test_value * ureg.joule

        # Serialize and deserialize
        serialized = original_section.m_to_dict()
        reconstructed_section = TestUnitSerializationSection.m_from_dict(serialized)

        # Check that units and bounds are preserved
        assert hasattr(reconstructed_section.bounded_quantity, 'magnitude')
        assert reconstructed_section.bounded_quantity.magnitude == test_value
        assert str(reconstructed_section.bounded_quantity.units) == 'joule'

        # Check that bounds checking still works
        invalid_value = 15.0
        with pytest.raises(ValueError):
            reconstructed_section.bounded_quantity = invalid_value * ureg.joule
