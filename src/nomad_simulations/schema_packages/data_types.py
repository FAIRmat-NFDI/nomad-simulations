#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any, TypeVar, Union

import numpy as np
from nomad.metainfo.data_type import ExactNumber, InexactNumber

T = TypeVar('T', bound='BoundedDataType')


def _flatten_values(data: Any) -> Generator[Any, None, None]:
    """Generator that yields all scalar values from nested list/array structure."""
    if isinstance(data, np.ndarray):
        yield from data.flatten()
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, list):
                yield from _flatten_values(item)
            else:
                yield item
    else:
        yield data


def _check_bounds(
    value: Union[int, float],
    min_value: float,
    max_value: float,
    min_inclusive: bool,
    max_inclusive: bool,
) -> bool:
    """Check if a single value is within the specified bounds."""
    # lower bound
    if np.isfinite(min_value):
        if min_inclusive:
            if value < min_value:
                return False
        else:
            if value <= min_value:
                return False

    # upper bound
    if np.isfinite(max_value):
        if max_inclusive:
            if value > max_value:
                return False
        else:
            if value >= max_value:
                return False

    return True


def _get_bounds_str(
    min_value: float, max_value: float, min_inclusive: bool, max_inclusive: bool
) -> str:
    """Get string representation of bounds."""
    left = '[' if min_inclusive else '('
    right = ']' if max_inclusive else ')'

    min_str = str(min_value) if np.isfinite(min_value) else '-∞'
    max_str = str(max_value) if np.isfinite(max_value) else '∞'

    return f'{left}{min_str}, {max_str}{right}'


class BoundedDataType(ABC):
    """
    Abstract base class for bounded data types with configurable bounds.
    
    Provides common functionality for setting bounds and validation logic.
    Bounds are by default +/- infinity (`float('inf')`, `float('-inf')` respectively).
    """

    __slots__ = ('_min_value', '_max_value', '_min_inclusive', '_max_inclusive')
    _error_message_prefix: str = 'All values'
    _additional_convertible_types: set = {}

    def __init__(self) -> None:
        self._min_value = float('-inf')
        self._max_value = float('inf')
        self._min_inclusive = True
        self._max_inclusive = True

    def min(self, value: Union[int, float], *, inclusive: bool = True) -> T:
        """Set minimum bound. Supports +/- infinity."""
        self._min_value = value
        self._min_inclusive = inclusive
        return self

    def max(self, value: Union[int, float], *, inclusive: bool = True) -> T:
        """Set maximum bound. Supports +/- infinity."""
        self._max_value = value
        self._max_inclusive = inclusive
        return self

    def convertible_from(self, other: Any) -> bool:
        """Check if this data type can convert from another type."""
        base_types = {np.int64, np.int32, np.int16, np.int8, 
                     np.float64, np.float32, np.float16}
        return other in self._additional_convertible_types + base_types

    @abstractmethod
    def _filter_values_for_validation(self, flat_values: list[Any]) -> list[Any]:
        """Filter values for validation (e.g., remove NaN for floats)."""
        pass

    def _validate_bounds(self, normalized_value: Any) -> None:
        """Common bounds validation logic."""
        flat_values = list(_flatten_values(normalized_value))
        valid_values = self._filter_values_for_validation(flat_values)
        
        if valid_values:
            invalid_values = [
                v for v in valid_values 
                if not _check_bounds(
                    v, self._min_value, self._max_value, 
                    self._min_inclusive, self._max_inclusive
                )
            ]
            
            if invalid_values:
                min_val = min(valid_values)
                max_val = max(valid_values)
                bounds = _get_bounds_str(
                    self._min_value, self._max_value, 
                    self._min_inclusive, self._max_inclusive
                )
                raise ValueError(
                    f'{self._error_message_prefix} must be in {bounds}, got range [{min_val}, {max_val}]'
                )


class BoundedInt(BoundedDataType, ExactNumber):
    """
    Integer data type with configurable bounds, i.e. bound value and inclusion.
    Bounds are by default +/- infinity (`float('inf')`, `float('-inf')` respectively).

    Examples:
        BoundedInt().min(1)                    # >= 1 (positive integers)
        BoundedInt().min(0)                    # >= 0 (non-negative integers)
        BoundedInt().min(1, inclusive=False)   # > 1
        BoundedInt().max(10)                   # <= 10
        BoundedInt().min(1).max(10)            # 1 <= value <= 10
    """
    
    _error_message_prefix = 'All values'
    _additional_convertible_types = {int}

    def __init__(self, *, dtype: type[int | np.int32] = int):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (int, np.int32, np.int64):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        ExactNumber.__init__(self, dtype)
        BoundedDataType.__init__(self)

    def _filter_values_for_validation(self, flat_values: list[Any]) -> list[Any]:
        """No filtering needed for integers - all values are valid for bounds checking."""
        return flat_values

    def normalize(self, value: Any, **kwargs: Any) -> Any:
        normalized_value = ExactNumber.normalize(self, value, **kwargs)

        if normalized_value is None:
            return None

        self._validate_bounds(normalized_value)
        return normalized_value


class BoundedFloat(BoundedDataType, InexactNumber):
    """
    Float data type with configurable bounds, i.e. bound value and inclusion.
    Bounds are by default +/- infinity (`float('inf')`, `float('-inf')` respectively).
    NaN values (`float('nan')`) are allowed and are not subject to any validity check.

    Examples:
        BoundedFloat().min(0)                          # >= 0 (non-negative)
        BoundedFloat().min(0, inclusive=False)         # > 0 (positive)
        BoundedFloat().min(0).max(1)                   # [0, 1] (unit interval)
        BoundedFloat().min(0).max(1, inclusive=False)  # [0, 1)
        BoundedFloat().max(0)                          # <= 0 (non-positive)
    """
    
    _error_message_prefix = 'All non-NaN values'
    _additional_convertible_types = {float}

    def __init__(self, *, dtype: type[float | np.float64] = float):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (float, np.float64, np.float32):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        InexactNumber.__init__(self, dtype)
        BoundedDataType.__init__(self)

    def _filter_values_for_validation(self, flat_values: list[Any]) -> list[Any]:
        """Filter out NaN values for float bounds checking."""
        return [v for v in flat_values if not (isinstance(v, float) and np.isnan(v))]

    def normalize(self, value: Any, **kwargs: Any) -> Any:
        normalized_value = InexactNumber.normalize(self, value, **kwargs)

        if normalized_value is None:
            return None

        self._validate_bounds(normalized_value)
        return normalized_value


# aliases for common use cases
StrictlyPositiveInt = lambda: BoundedInt().min(1)  # >= 1 integers
PositiveInt = lambda: BoundedInt().min(0)  # >= 0 integers (non-negative)
StrictlyPositiveFloat = lambda: BoundedFloat().min(0, inclusive=False)  # > 0 floats
PositiveFloat = lambda: BoundedFloat().min(0)  # >= 0 floats (non-negative)
UnitFloat = lambda: BoundedFloat().min(0).max(1)  # [0, 1] floats
