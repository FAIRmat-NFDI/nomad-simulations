import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.data_types import (
    PositiveFloat,
    PositiveInt,
    UnitFloat,
)

from . import logger


class TestPositiveInt:
    """
    Test the `PositiveInt` class defined in data_types.py
    """

    def test_init_default(self):
        """Test default initialization."""
        pos_int = PositiveInt()
        assert pos_int._dtype == int
        assert pos_int._np_base == np.integer

    def test_init_with_dtype(self):
        """Test initialization with specific dtype."""
        pos_int = PositiveInt(dtype=np.int32)
        assert pos_int._dtype == np.int32

    def test_valid_positive_scalar(self):
        """Test normalization of valid positive scalar values."""
        pos_int = PositiveInt()
        
        # Test various positive values
        assert pos_int.normalize(1) == 1
        assert pos_int.normalize(42) == 42
        assert pos_int.normalize(np.int32(5)) == np.int32(5)

    def test_invalid_zero_and_negative_scalar(self):
        """Test that zero and negative values raise ValueError."""
        pos_int = PositiveInt()
        
        with pytest.raises(ValueError, match="Value must be positive"):
            pos_int.normalize(0)
        
        with pytest.raises(ValueError, match="Value must be positive"):
            pos_int.normalize(-1)
        
        with pytest.raises(ValueError, match="Value must be positive"):
            pos_int.normalize(-42)

    def test_valid_positive_array(self):
        """Test normalization of valid positive arrays."""
        pos_int = PositiveInt()
        
        # Test list
        result = pos_int.normalize([1, 2, 3, 10])
        assert result == [1, 2, 3, 10]
        
        # Test numpy array
        arr = np.array([5, 15, 25])
        result = pos_int.normalize(arr)
        np.testing.assert_array_equal(result, arr)

    def test_invalid_array_with_non_positive(self):
        """Test that arrays containing zero or negative values raise ValueError."""
        pos_int = PositiveInt()
        
        # Test list with zero
        with pytest.raises(ValueError, match="All values must be positive"):
            pos_int.normalize([1, 0, 3])
        
        # Test list with negative
        with pytest.raises(ValueError, match="All values must be positive"):
            pos_int.normalize([1, 2, -1])
        
        # Test numpy array with zero
        with pytest.raises(ValueError, match="All values must be positive"):
            pos_int.normalize(np.array([1, 0, 3]))

    def test_none_value(self):
        """Test that None values are handled correctly."""
        pos_int = PositiveInt()
        assert pos_int.normalize(None) is None


class TestPositiveFloat:
    """
    Test the `PositiveFloat` class defined in data_types.py
    """

    def test_init_default(self):
        """Test default initialization."""
        pos_float = PositiveFloat()
        assert pos_float._dtype == float
        assert pos_float._np_base == np.inexact

    def test_valid_positive_scalar(self):
        """Test normalization of valid positive scalar values."""
        pos_float = PositiveFloat()
        
        # Test various positive values
        assert pos_float.normalize(1.0) == 1.0
        assert pos_float.normalize(0.5) == 0.5
        assert pos_float.normalize(42.7) == 42.7
        assert pos_float.normalize(np.float64(3.14)) == np.float64(3.14)

    def test_invalid_zero_and_negative_scalar(self):
        """Test that zero and negative values raise ValueError."""
        pos_float = PositiveFloat()
        
        with pytest.raises(ValueError, match="Value must be positive"):
            pos_float.normalize(0.0)
        
        with pytest.raises(ValueError, match="Value must be positive"):
            pos_float.normalize(-1.5)
        
        with pytest.raises(ValueError, match="Value must be positive"):
            pos_float.normalize(-0.001)

    def test_nan_handling(self):
        """Test that NaN values are allowed."""
        pos_float = PositiveFloat()
        
        result = pos_float.normalize(float('nan'))
        assert np.isnan(result)

    def test_valid_positive_array(self):
        """Test normalization of valid positive arrays."""
        pos_float = PositiveFloat()
        
        # Test list
        result = pos_float.normalize([1.0, 2.5, 3.7])
        assert result == [1.0, 2.5, 3.7]
        
        # Test numpy array
        arr = np.array([0.1, 1.5, 2.5])
        result = pos_float.normalize(arr)
        np.testing.assert_array_equal(result, arr)

    def test_array_with_nan(self):
        """Test arrays containing NaN values."""
        pos_float = PositiveFloat()
        
        # List with NaN should work
        result = pos_float.normalize([1.0, float('nan'), 3.0])
        assert result[0] == 1.0
        assert np.isnan(result[1])
        assert result[2] == 3.0

    def test_invalid_array_with_non_positive(self):
        """Test that arrays containing zero or negative values raise ValueError."""
        pos_float = PositiveFloat()
        
        # Test array with mixed NaN and negative (should fail)
        with pytest.raises(ValueError, match="All non-NaN values must be positive"):
            pos_float.normalize([1.0, -2.0, float('nan')])


class TestUnitFloat:
    """
    Test the `UnitFloat` class defined in data_types.py
    """

    def test_init_default(self):
        """Test default initialization with inclusive bounds."""
        unit_float = UnitFloat()
        assert unit_float._dtype == float
        assert unit_float._np_base == np.inexact
        assert unit_float._min_inclusive is True
        assert unit_float._max_inclusive is True

    def test_chainable_methods(self):
        """Test that the chainable methods work correctly."""
        # Test exclude_min
        unit_float = UnitFloat().exclude_min()
        assert unit_float._min_inclusive is False
        assert unit_float._max_inclusive is True
        
        # Test exclude_max
        unit_float = UnitFloat().exclude_max()
        assert unit_float._min_inclusive is True
        assert unit_float._max_inclusive is False
        
        # Test chaining both
        unit_float = UnitFloat().exclude_min().exclude_max()
        assert unit_float._min_inclusive is False
        assert unit_float._max_inclusive is False

    def test_valid_values_inclusive_bounds(self):
        """Test valid values with default inclusive bounds [0, 1]."""
        unit_float = UnitFloat()
        
        # Test boundary values
        assert unit_float.normalize(0.0) == 0.0
        assert unit_float.normalize(1.0) == 1.0
        
        # Test internal values
        assert unit_float.normalize(0.5) == 0.5
        assert unit_float.normalize(0.999) == 0.999
        assert unit_float.normalize(0.001) == 0.001

    def test_invalid_values_inclusive_bounds(self):
        """Test invalid values with default inclusive bounds [0, 1]."""
        unit_float = UnitFloat()
        
        with pytest.raises(ValueError, match=r"Value must be in \[0, 1\]"):
            unit_float.normalize(-0.1)
        
        with pytest.raises(ValueError, match=r"Value must be in \[0, 1\]"):
            unit_float.normalize(1.1)
        
        with pytest.raises(ValueError, match=r"Value must be in \[0, 1\]"):
            unit_float.normalize(2.0)

    def test_exclusive_min_bound(self):
        """Test exclusive minimum bound (0, 1]."""
        unit_float = UnitFloat().exclude_min()
        
        # 0 should now be invalid
        with pytest.raises(ValueError, match=r"Value must be in \(0, 1\]"):
            unit_float.normalize(0.0)
        
        # 1 should still be valid
        assert unit_float.normalize(1.0) == 1.0
        
        # Small positive values should be valid
        assert unit_float.normalize(0.001) == 0.001

    def test_exclusive_max_bound(self):
        """Test exclusive maximum bound [0, 1)."""
        unit_float = UnitFloat().exclude_max()
        
        # 1 should now be invalid
        with pytest.raises(ValueError, match=r"Value must be in \[0, 1\)"):
            unit_float.normalize(1.0)
        
        # 0 should still be valid
        assert unit_float.normalize(0.0) == 0.0
        
        # Values close to 1 should be valid
        assert unit_float.normalize(0.999) == 0.999

    def test_exclusive_both_bounds(self):
        """Test exclusive both bounds (0, 1)."""
        unit_float = UnitFloat().exclude_min().exclude_max()
        
        # Both 0 and 1 should be invalid
        with pytest.raises(ValueError, match=r"Value must be in \(0, 1\)"):
            unit_float.normalize(0.0)
        
        with pytest.raises(ValueError, match=r"Value must be in \(0, 1\)"):
            unit_float.normalize(1.0)
        
        # Internal values should be valid
        assert unit_float.normalize(0.5) == 0.5

    def test_valid_arrays(self):
        """Test valid arrays with different bound configurations."""
        # Default inclusive bounds
        unit_float = UnitFloat()
        result = unit_float.normalize([0.0, 0.5, 1.0])
        assert result == [0.0, 0.5, 1.0]
        
        # Numpy array
        arr = np.array([0.1, 0.5, 0.9])
        result = unit_float.normalize(arr)
        np.testing.assert_array_equal(result, arr)

    def test_invalid_arrays(self):
        """Test invalid arrays."""
        unit_float = UnitFloat()
        
        # Array with value outside bounds
        with pytest.raises(ValueError, match=r"All non-NaN values must be in \[0, 1\]"):
            unit_float.normalize([0.5, 1.5, 0.8])
        
        with pytest.raises(ValueError, match=r"All non-NaN values must be in \[0, 1\]"):
            unit_float.normalize(np.array([-0.1, 0.5, 0.8]))

    def test_arrays_with_nan(self):
        """Test arrays containing NaN values."""
        unit_float = UnitFloat()
        
        # NaN should be allowed
        result = unit_float.normalize([0.5, float('nan'), 0.8])
        assert result[0] == 0.5
        assert np.isnan(result[1])
        assert result[2] == 0.8

    def test_bounds_string_representation(self):
        """Test the bounds string representation helper method."""
        # Default inclusive
        unit_float = UnitFloat()
        assert unit_float._get_bounds_str() == "[0, 1]"
        
        # Exclusive min
        unit_float = UnitFloat().exclude_min()
        assert unit_float._get_bounds_str() == "(0, 1]"
        
        # Exclusive max
        unit_float = UnitFloat().exclude_max()
        assert unit_float._get_bounds_str() == "[0, 1)"
        
        # Exclusive both
        unit_float = UnitFloat().exclude_min().exclude_max()
        assert unit_float._get_bounds_str() == "(0, 1)"

    def test_none_value(self):
        """Test that None values are handled correctly."""
        unit_float = UnitFloat()
        assert unit_float.normalize(None) is None