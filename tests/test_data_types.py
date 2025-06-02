from unittest.mock import Mock

import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.data_types import (
    BoundedFloat,
    BoundedInt,
    PositiveFloat,
    PositiveInt,
    StrictlyPositiveFloat,
    StrictlyPositiveInt,
    UnitFloat,
)

from . import logger


def setup_datatype_for_testing(datatype_instance, shape=None):
    """Helper function to set up a datatype instance for testing."""
    mock_definition = Mock()
    mock_definition.shape = shape
    mock_definition.unit = None
    mock_definition.flexible_unit = False
    datatype_instance.attach_definition(mock_definition)
    return datatype_instance


class TestBoundedInt:
    """
    Test the `BoundedInt` class defined in data_types.py
    """

    def test_init_default(self):
        """Test default initialization with no bounds."""
        bounded_int = BoundedInt()
        assert bounded_int._dtype == int
        assert bounded_int._min_value == float('-inf')
        assert bounded_int._max_value == float('inf')
        assert bounded_int._min_inclusive is True
        assert bounded_int._max_inclusive is True

    def test_chainable_methods(self):
        """Test that the chainable methods work correctly."""
        # Test min
        bounded_int = BoundedInt().min(5)
        assert bounded_int._min_value == 5
        assert bounded_int._min_inclusive is True
        
        # Test max
        bounded_int = BoundedInt().max(10)
        assert bounded_int._max_value == 10
        assert bounded_int._max_inclusive is True
        
        # Test exclusive bounds
        bounded_int = BoundedInt().min(5, inclusive=False).max(10, inclusive=False)
        assert bounded_int._min_value == 5
        assert bounded_int._max_value == 10
        assert bounded_int._min_inclusive is False
        assert bounded_int._max_inclusive is False

    def test_unbounded_values(self):
        """Test normalization with no bounds (all values valid)."""
        bounded_int = setup_datatype_for_testing(BoundedInt(), shape=None)
        
        assert bounded_int.normalize(0) == 0
        assert bounded_int.normalize(-100) == -100
        assert bounded_int.normalize(1000) == 1000

    def test_min_bound_inclusive(self):
        """Test minimum bound inclusive (>= 5)."""
        bounded_int = setup_datatype_for_testing(BoundedInt().min(5), shape=None)
        
        # Valid values
        assert bounded_int.normalize(5) == 5
        assert bounded_int.normalize(10) == 10
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[5, ∞\]'):
            bounded_int.normalize(4)

    def test_min_bound_exclusive(self):
        """Test minimum bound exclusive (> 5)."""
        bounded_int = setup_datatype_for_testing(BoundedInt().min(5, inclusive=False), shape=None)
        
        # Valid values
        assert bounded_int.normalize(6) == 6
        assert bounded_int.normalize(10) == 10
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \(5, ∞\]'):
            bounded_int.normalize(5)

    def test_max_bound_inclusive(self):
        """Test maximum bound inclusive (<= 10)."""
        bounded_int = setup_datatype_for_testing(BoundedInt().max(10), shape=None)
        
        # Valid values
        assert bounded_int.normalize(10) == 10
        assert bounded_int.normalize(-5) == -5
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[-∞, 10\]'):
            bounded_int.normalize(11)

    def test_both_bounds(self):
        """Test both minimum and maximum bounds [5, 10]."""
        bounded_int = setup_datatype_for_testing(BoundedInt().min(5).max(10), shape=None)
        
        # Valid values
        assert bounded_int.normalize(5) == 5
        assert bounded_int.normalize(7) == 7
        assert bounded_int.normalize(10) == 10
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[5, 10\]'):
            bounded_int.normalize(4)
        
        with pytest.raises(ValueError, match=r'Value must be in \[5, 10\]'):
            bounded_int.normalize(11)

    def test_arrays(self):
        """Test array validation."""
        bounded_int = setup_datatype_for_testing(BoundedInt().min(0).max(10), shape=['*'])
        
        # Valid arrays
        result = bounded_int.normalize([0, 5, 10])
        assert result == [0, 5, 10]
        
        arr = np.array([1, 3, 7])
        result = bounded_int.normalize(arr)
        np.testing.assert_array_equal(result, arr)
        
        # Invalid arrays
        with pytest.raises(ValueError, match=r'All values must be in \[0, 10\]'):
            bounded_int.normalize([-1, 5, 10])

    def test_infinity_bounds(self):
        """Test bounds with infinity values."""
        bounded_int = setup_datatype_for_testing(BoundedInt().min(float('-inf')).max(float('inf')), shape=None)
        
        # Should accept any value
        assert bounded_int.normalize(-1000) == -1000
        assert bounded_int.normalize(1000) == 1000

    def test_none_value(self):
        """Test that None values are handled correctly."""
        bounded_int = setup_datatype_for_testing(BoundedInt().min(0), shape=None)
        assert bounded_int.normalize(None) is None


class TestBoundedFloat:
    """
    Test the `BoundedFloat` class defined in data_types.py
    """

    def test_init_default(self):
        """Test default initialization with no bounds."""
        bounded_float = BoundedFloat()
        assert bounded_float._dtype == float
        assert bounded_float._min_value == float('-inf')
        assert bounded_float._max_value == float('inf')
        assert bounded_float._min_inclusive is True
        assert bounded_float._max_inclusive is True

    def test_chainable_methods(self):
        """Test that the chainable methods work correctly."""
        # Test min and max chaining
        bounded_float = BoundedFloat().min(0.5).max(2.5)
        assert bounded_float._min_value == 0.5
        assert bounded_float._max_value == 2.5
        assert bounded_float._min_inclusive is True
        assert bounded_float._max_inclusive is True

    def test_min_bound_exclusive(self):
        """Test minimum bound exclusive (> 0)."""
        bounded_float = setup_datatype_for_testing(BoundedFloat().min(0, inclusive=False), shape=None)
        
        # Valid values
        assert bounded_float.normalize(0.001) == 0.001
        assert bounded_float.normalize(1.5) == 1.5
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \(0, ∞\]'):
            bounded_float.normalize(0.0)
        
        with pytest.raises(ValueError, match=r'Value must be in \(0, ∞\]'):
            bounded_float.normalize(-0.5)

    def test_unit_interval(self):
        """Test unit interval [0, 1]."""
        bounded_float = setup_datatype_for_testing(BoundedFloat().min(0).max(1), shape=None)
        
        # Valid values
        assert bounded_float.normalize(0.0) == 0.0
        assert bounded_float.normalize(0.5) == 0.5
        assert bounded_float.normalize(1.0) == 1.0
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[0, 1\]'):
            bounded_float.normalize(-0.1)
        
        with pytest.raises(ValueError, match=r'Value must be in \[0, 1\]'):
            bounded_float.normalize(1.1)

    def test_nan_handling(self):
        """Test that NaN values are allowed."""
        bounded_float = setup_datatype_for_testing(BoundedFloat().min(0).max(1), shape=None)
        
        result = bounded_float.normalize(float('nan'))
        assert np.isnan(result)

    def test_arrays_with_nan(self):
        """Test arrays containing NaN values."""
        bounded_float = setup_datatype_for_testing(BoundedFloat().min(0).max(1), shape=['*'])
        
        # NaN should be allowed
        result = bounded_float.normalize([0.5, float('nan'), 0.8])
        assert result[0] == 0.5
        assert np.isnan(result[1])
        assert result[2] == 0.8
        
        # Mixed valid and invalid (non-NaN)
        with pytest.raises(ValueError, match=r'All non-NaN values must be in \[0, 1\]'):
            bounded_float.normalize([0.5, 1.5, float('nan')])

    def test_infinity_values(self):
        """Test bounds with infinity."""
        bounded_float = setup_datatype_for_testing(BoundedFloat().min(float('-inf')), shape=None)
        
        # Should accept any finite value
        assert bounded_float.normalize(-1e10) == -1e10
        assert bounded_float.normalize(1e10) == 1e10
        
        # Should also accept infinity
        assert bounded_float.normalize(float('inf')) == float('inf')

    def test_none_value(self):
        """Test that None values are handled correctly."""
        bounded_float = setup_datatype_for_testing(BoundedFloat().min(0), shape=None)
        assert bounded_float.normalize(None) is None


class TestConvenienceAliases:
    """
    Test the convenience alias functions.
    """

    def test_strictly_positive_int(self):
        """Test StrictlyPositiveInt (>= 1)."""
        pos_int = setup_datatype_for_testing(StrictlyPositiveInt(), shape=None)
        
        # Valid values
        assert pos_int.normalize(1) == 1
        assert pos_int.normalize(42) == 42
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[1, ∞\]'):
            pos_int.normalize(0)

    def test_positive_int(self):
        """Test PositiveInt (>= 0, non-negative)."""
        pos_int = setup_datatype_for_testing(PositiveInt(), shape=None)
        
        # Valid values
        assert pos_int.normalize(0) == 0
        assert pos_int.normalize(1) == 1
        assert pos_int.normalize(42) == 42
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[0, ∞\]'):
            pos_int.normalize(-1)

    def test_strictly_positive_float(self):
        """Test StrictlyPositiveFloat (> 0)."""
        pos_float = setup_datatype_for_testing(StrictlyPositiveFloat(), shape=None)
        
        # Valid values
        assert pos_float.normalize(0.001) == 0.001
        assert pos_float.normalize(1.5) == 1.5
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \(0, ∞\]'):
            pos_float.normalize(0.0)

    def test_positive_float(self):
        """Test PositiveFloat (>= 0, non-negative)."""
        pos_float = setup_datatype_for_testing(PositiveFloat(), shape=None)
        
        # Valid values
        assert pos_float.normalize(0.0) == 0.0
        assert pos_float.normalize(0.5) == 0.5
        assert pos_float.normalize(1.5) == 1.5
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[0, ∞\]'):
            pos_float.normalize(-0.1)

    def test_unit_float(self):
        """Test UnitFloat ([0, 1])."""
        unit_float = setup_datatype_for_testing(UnitFloat(), shape=None)
        
        # Valid values
        assert unit_float.normalize(0.0) == 0.0
        assert unit_float.normalize(0.5) == 0.5
        assert unit_float.normalize(1.0) == 1.0
        
        # Invalid values
        with pytest.raises(ValueError, match=r'Value must be in \[0, 1\]'):
            unit_float.normalize(-0.1)
        
        with pytest.raises(ValueError, match=r'Value must be in \[0, 1\]'):
            unit_float.normalize(1.1)


class TestBoundsStringRepresentation:
    """
    Test the bounds string representation.
    """

    def test_various_bound_representations(self):
        """Test different bound string representations."""
        # Unbounded
        bounded_int = BoundedInt()
        assert bounded_int._get_bounds_str() == '[-∞, ∞]'
        
        # Min only
        bounded_int = BoundedInt().min(5)
        assert bounded_int._get_bounds_str() == '[5, ∞]'
        
        # Max only
        bounded_int = BoundedInt().max(10)
        assert bounded_int._get_bounds_str() == '[-∞, 10]'
        
        # Both bounds, mixed inclusivity
        bounded_int = BoundedInt().min(5, inclusive=False).max(10)
        assert bounded_int._get_bounds_str() == '(5, 10]'
        
        # Exclusive both
        bounded_float = BoundedFloat().min(0, inclusive=False).max(1, inclusive=False)
        assert bounded_float._get_bounds_str() == '(0, 1)'