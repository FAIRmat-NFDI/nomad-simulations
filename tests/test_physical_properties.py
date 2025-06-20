from typing import Optional, Union

import numpy as np
import pytest
from _pytest.logging import LoggingPlugin
from nomad.datamodel import EntryArchive
from nomad.metainfo import Quantity
from nomad.units import ureg

from nomad_simulations.schema_packages.physical_property import (
    PhysicalProperty,
    same_shapes,
)

# from nomad_simulations.schema_packages.variables import Variables
from . import logger


class DummyPhysicalProperty(PhysicalProperty):
    value = Quantity(
        type=np.float64,
        unit='eV',
        shape=['*', '*', '*', '*'],
        description="""
        This value is defined in order to test the `__setattr__` method in `PhysicalProperty`.
        """,
    )


class TestPhysicalProperty:
    """
    Test the `PhysicalProperty` class defined in `physical_property.py`.
    """

    def test_setattr_value(self):
        """
        Test the `__setattr__` method when setting the `value` quantity of a physical property.
        """
        physical_property = DummyPhysicalProperty(
            source='simulation',
            # variables=[Variables(n_points=4), Variables(n_points=10)],
        )
        # `physical_property.value` must have full_shape=[4, 10, 3, 3]
        value = np.ones((4, 10, 3, 3)) * ureg.eV
        # assert physical_property.full_shape == list(value.shape)
        physical_property.value = value
        assert np.all(physical_property.value == value)

    def test_is_derived(self):
        """
        Test the `normalize` and `_is_derived` methods.
        """
        # Testing a directly parsed physical property
        not_derived_physical_property = PhysicalProperty(source='simulation')
        assert not_derived_physical_property._is_derived() is False
        not_derived_physical_property.normalize(EntryArchive(), logger)
        assert not_derived_physical_property.is_derived is False
        # Testing a derived physical property
        derived_physical_property = PhysicalProperty(
            source='analysis',
            physical_property_ref=not_derived_physical_property,
        )
        assert derived_physical_property._is_derived() is True
        derived_physical_property.normalize(EntryArchive(), logger)
        assert derived_physical_property.is_derived is True


@pytest.mark.parametrize(
    'quantities, class_attrs, target, warning_text',
    [
        # Matching shapes - no warning
        (
            {'arr1': {0}, 'arr2': {0}},
            {'arr1': np.array([[1, 2], [3, 4]]), 'arr2': np.array([[5, 6], [7, 8]])},
            None,
            '',
        ),
        # Mismatched shapes - warning
        (
            {'arr1': {0}, 'arr2': {0}},
            {'arr1': np.array([[1, 2], [3, 4]]), 'arr2': np.array([[[1, 2]], [[3, 4]], [[5, 6]]])},
            None,
            "do not match",
        ),
        # Target shape matching - no warning
        (
            {'arr1': {0}, 'arr2': {1}},
            {'arr1': np.array([[1, 2], [3, 4], [5, 6]]), 'arr2': np.array([[1, 2, 3], [4, 5, 6]])},
            3,
            '',
        ),
        # Target shape mismatch - warning
        (
            {'arr1': {0}},
            {'arr1': np.array([[1, 2], [3, 4]])},
            5,
            "target shape 5",
        ),
        # Multiple dimensions matching - no warning
        (
            {'arr1': {0, 1}},
            {'arr1': np.array([[1, 2], [3, 4]])},
            None,
            '',
        ),
        # Multiple dimensions mismatch - warning
        (
            {'arr1': {0, 1}},
            {'arr1': np.array([[1, 2, 3], [4, 5, 6]])},
            None,
            "do not match",
        ),
        # Empty quantities - no warning
        (
            {},
            {'arr1': np.array([1, 2, 3])},
            None,
            '',
        ),
        # Missing attributes - no warning (ignored)
        (
            {'nonexistent': {0}},
            {'arr1': np.array([1, 2, 3])},
            None,
            '',
        ),
        # Non-array attribute - warning
        (
            {'not_array': {0}},
            {'not_array': "string"},
            None,
            "not array-like",
        ),
        # Invalid dimension index - warning
        (
            {'arr1': {5}},
            {'arr1': np.array([1, 2, 3])},
            None,
            "valid ranks",
        ),
    ],
)
def test_same_shapes(
    quantities: dict[str, set[int]], 
    class_attrs: dict[str, Union[np.ndarray, str]], 
    target: Optional[int], 
    warning_text: str, 
    caplog: LoggingPlugin
):
    """Test the same_shapes decorator with various scenarios."""
    kwargs = {}
    if target is not None:
        kwargs['target'] = target
    
    @same_shapes(quantities, **kwargs)
    class TestClass:
        pass
    
    # Set attributes on the class
    for attr_name, attr_value in class_attrs.items():
        setattr(TestClass, attr_name, attr_value)
    
    if warning_text:
        assert len(caplog.records) == 1
        assert warning_text in caplog.records[0].message
    else:
        assert len(caplog.records) == 0
