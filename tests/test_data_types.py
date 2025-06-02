from unittest.mock import Mock

import numpy as np
import pytest

from nomad_simulations.schema_packages.data_types import (
    BoundedFloat,
    BoundedInt,
)


def setup_datatype_for_testing(datatype_instance, shape=None):
    """Helper function to set up a datatype instance for testing."""
    mock_definition = Mock()
    mock_definition.shape = shape
    mock_definition.unit = None
    mock_definition.flexible_unit = False
    datatype_instance.attach_definition(mock_definition)
    return datatype_instance


class TestBoundedDataType:
    """
    Test the `BoundedDataType` base class functionality.
    """

    @pytest.mark.parametrize('datatype_class', [BoundedInt, BoundedFloat])
    def test_chainable_methods(self, datatype_class):
        """Test that chainable methods work and return self."""
        datatype = datatype_class()

        # Test min method
        result = datatype.min(5)
        assert result is datatype
        assert datatype._min_value == 5
        assert datatype._min_inclusive is True

        # Test max method
        result = datatype.max(10, inclusive=False)
        assert result is datatype
        assert datatype._max_value == 10
        assert datatype._max_inclusive is False

    @pytest.mark.parametrize(
        'datatype_class,test_types,expected_results',
        [
            (
                BoundedInt,
                [int, np.int32, np.int16, np.int8, float, np.float64, str],
                [True, True, True, True, False, False, False],
            ),
            (
                BoundedFloat,
                [float, np.float64, np.float32, np.float16, int, np.int32, str],
                [True, True, True, True, False, False, False],
            ),
        ],
    )
    def test_convertible_from(self, datatype_class, test_types, expected_results):
        """Test convertible_from method."""
        datatype = datatype_class()
        for test_type, expected in zip(test_types, expected_results):
            assert datatype.convertible_from(test_type) == expected

    @pytest.mark.parametrize(
        'datatype_class,valid_values,invalid_values',
        [
            (BoundedInt, [0, 5, 10], [-1, 11]),
            (BoundedFloat, [0.0, 0.5, 1.0], [-0.1, 11.1]),
        ],
    )
    def test_bounds_validation_integration(
        self, datatype_class, valid_values, invalid_values
    ):
        """Test the integrated bounds validation functionality."""
        datatype = setup_datatype_for_testing(
            datatype_class().min(0).max(10), shape=None
        )

        # Test valid values
        for value in valid_values:
            assert datatype.normalize(value) == value

        # Test invalid values
        for value in invalid_values:
            with pytest.raises(ValueError, match=r'must be in \[0, 10\]'):
                datatype.normalize(value)

    @pytest.mark.parametrize(
        'datatype_class,test_list,should_pass',
        [
            # BoundedInt valid cases
            (BoundedInt, [1, 2, 3, 4, 5], True),
            (BoundedInt, [0, 10], True),
            (BoundedInt, [5], True),
            (BoundedInt, [], True),
            # BoundedInt invalid cases
            (BoundedInt, [1, 2, 15, 4, 5], False),  # 15 out of bounds
            (BoundedInt, [-1, 5, 8], False),  # -1 out of bounds
            (BoundedInt, [0, 11], False),  # 11 out of bounds
            # BoundedFloat valid cases
            (BoundedFloat, [1.0, 2.5, 3.0, 4.5, 5.0], True),
            (BoundedFloat, [0.0, 10.0], True),
            (BoundedFloat, [5.5], True),
            (BoundedFloat, [], True),
            # BoundedFloat invalid cases
            (BoundedFloat, [1.0, 2.5, 15.0, 4.5, 5.0], False),  # 15.0 out of bounds
            (BoundedFloat, [-0.1, 5.5, 8.0], False),  # -0.1 out of bounds
            (BoundedFloat, [0.0, 10.1], False),  # 10.1 out of bounds
        ],
    )
    def test_nested_structure_validation(self, datatype_class, test_list, should_pass):
        """Test validation of list structures."""
        datatype = setup_datatype_for_testing(
            datatype_class().min(0).max(10), shape=['*']
        )

        import numpy as np

        if should_pass:
            result = datatype.normalize(test_list)
            # Handle both numpy array and list results
            if isinstance(result, np.ndarray):
                assert np.array_equal(result, test_list)
            else:
                assert result == test_list
        else:
            with pytest.raises(ValueError, match=r'must be in \[0, 10\]'):
                datatype.normalize(test_list)


class TestBoundedInt:
    """
    Test BoundedInt-specific functionality.
    """

    @pytest.mark.parametrize(
        'dtype,should_pass',
        [
            # Valid dtypes
            (int, True),
            (np.int32, True),
            # Invalid dtypes
            (np.int64, False),
            (float, False),
            (np.float32, False),
            (np.float64, False),
            (str, False),
            (bool, False),
        ],
    )
    def test_dtype_validation(self, dtype, should_pass):
        """Test that only valid integer dtypes are accepted."""
        if should_pass:
            BoundedInt(dtype=dtype)  # Should not raise
        else:
            with pytest.raises(ValueError, match='Invalid dtype'):
                BoundedInt(dtype=dtype)

    def test_integer_specific_validation(self):
        """Test integer-specific validation behavior."""
        bounded_int = setup_datatype_for_testing(
            BoundedInt().min(0).max(10), shape=None
        )
        assert bounded_int._filter_values_for_validation([1, 2, 3]) == [1, 2, 3]


class TestBoundedFloat:
    """
    Test BoundedFloat-specific functionality.
    """

    @pytest.mark.parametrize(
        'dtype,should_pass',
        [
            # Valid dtypes
            (float, True),
            (np.float32, True),
            (np.float64, True),
            # Invalid dtypes
            (int, False),
            (np.int32, False),
            (np.int64, False),
            (str, False),
            (bool, False),
            (complex, False),
        ],
    )
    def test_dtype_validation(self, dtype, should_pass):
        """Test that only valid float dtypes are accepted."""
        if should_pass:
            BoundedFloat(dtype=dtype)  # Should not raise
        else:
            with pytest.raises(ValueError, match='Invalid dtype'):
                BoundedFloat(dtype=dtype)

    @pytest.mark.parametrize(
        'test_value,shape,should_pass',
        [
            # Scalar NaN values
            (float('nan'), None, True),
            # Arrays with valid values and NaN
            ([0.5, float('nan'), 0.8], ['*'], True),
            ([0.0, 1.0, float('nan')], ['*'], True),
            ([float('nan')], ['*'], True),
            # Arrays with invalid non-NaN values (should fail)
            ([0.5, 1.5, float('nan')], ['*'], False),
            ([-0.1, float('nan'), 0.5], ['*'], False),
        ],
    )
    def test_nan_handling(self, test_value, shape, should_pass):
        """Test that NaN values are allowed and filtered from validation."""
        bounded_float = setup_datatype_for_testing(
            BoundedFloat().min(0).max(1), shape=shape
        )

        if should_pass:
            result = bounded_float.normalize(test_value)
            if isinstance(test_value, list):
                # Check that result has same structure and NaN positions
                assert len(result) == len(test_value)
                for i, (orig, res) in enumerate(zip(test_value, result)):
                    if np.isnan(orig):
                        assert np.isnan(res), f'NaN not preserved at position {i}'
                    else:
                        assert res == orig, f'Value mismatch at position {i}'
            else:
                assert np.isnan(result), 'Scalar NaN not preserved'
        else:
            with pytest.raises(
                ValueError, match=r'All non-NaN values must be in \[0, 1\]'
            ):
                bounded_float.normalize(test_value)

    def test_float_specific_validation(self):
        """Test float-specific validation behavior."""
        bounded_float = setup_datatype_for_testing(
            BoundedFloat().min(0).max(1), shape=None
        )

        test_values = [0.5, float('nan'), 0.8]
        filtered = bounded_float._filter_values_for_validation(test_values)
        assert filtered == [0.5, 0.8]  # NaN should be filtered out


class TestBoundsStringRepresentation:
    """
    Test the bounds string representation.
    """

    @pytest.mark.parametrize(
        'datatype_class,config,expected_str',
        [
            (BoundedInt, {}, '[-∞, ∞]'),
            (BoundedInt, {'min': (5, True)}, '[5, ∞]'),
            (BoundedInt, {'max': (10, True)}, '[-∞, 10]'),
            (BoundedInt, {'min': (5, False), 'max': (10, True)}, '(5, 10]'),
            (BoundedFloat, {'min': (0, False), 'max': (1, False)}, '(0, 1)'),
        ],
    )
    def test_bounds_string_representation(self, datatype_class, config, expected_str):
        """Test different bound string representations."""
        datatype = datatype_class()

        if 'min' in config:
            value, inclusive = config['min']
            datatype.min(value, inclusive=inclusive)
        if 'max' in config:
            value, inclusive = config['max']
            datatype.max(value, inclusive=inclusive)

        from nomad_simulations.schema_packages.data_types import _get_bounds_str

        actual_str = _get_bounds_str(
            datatype._min_value,
            datatype._max_value,
            datatype._min_inclusive,
            datatype._max_inclusive,
        )
        assert actual_str == expected_str
