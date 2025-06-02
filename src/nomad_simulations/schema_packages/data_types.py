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

import numpy as np
from nomad.metainfo.data_type import ExactNumber, InexactNumber


class BoundedInt(ExactNumber):
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

    __slots__ = ('_min_value', '_max_value', '_min_inclusive', '_max_inclusive')

    def __init__(self, *, dtype: type[int | np.int32] = int):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (int, np.int32, np.int64):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._min_value = float('-inf')
        self._max_value = float('inf')
        self._min_inclusive = True
        self._max_inclusive = True

    def min(self, value, *, inclusive: bool = True):
        """Set minimum bound. Supports +/- infinity."""
        self._min_value = value
        self._min_inclusive = inclusive
        return self

    def max(self, value, *, inclusive: bool = True):
        """Set maximum bound. Supports +/- infinity."""
        self._max_value = value
        self._max_inclusive = inclusive
        return self

    def convertible_from(self, other):
        if other in (int, np.int64, np.int32, np.int16, np.int8):
            return True
        return False

    def normalize(self, value, **kwargs):
        normalized_value = super().normalize(value, **kwargs)

        if normalized_value is None:
            return normalized_value

        # Handle arrays
        if isinstance(normalized_value, (list, np.ndarray)):
            if isinstance(normalized_value, np.ndarray):
                if not np.all(self._is_in_bounds_vectorized(normalized_value)):
                    min_val = np.min(normalized_value)
                    max_val = np.max(normalized_value)
                    bounds = self._get_bounds_str()
                    raise ValueError(
                        f'All values must be in {bounds}, got range [{min_val}, {max_val}]'
                    )
            else:  # list
                for v in normalized_value:
                    if not self._is_in_bounds(v):
                        min_val = min(normalized_value)
                        max_val = max(normalized_value)
                        bounds = self._get_bounds_str()
                        raise ValueError(
                            f'All values must be in {bounds}, got range [{min_val}, {max_val}]'
                        )
        else:
            # Handle scalars
            if not self._is_in_bounds(normalized_value):
                bounds = self._get_bounds_str()
                raise ValueError(f'Value must be in {bounds}, got {normalized_value}')

        return normalized_value

    def _is_in_bounds(self, value):
        """Check if a single value is within bounds."""
        # Check minimum bound
        if np.isfinite(self._min_value):
            if self._min_inclusive:
                if value < self._min_value:
                    return False
            else:
                if value <= self._min_value:
                    return False

        # Check maximum bound
        if np.isfinite(self._max_value):
            if self._max_inclusive:
                if value > self._max_value:
                    return False
            else:
                if value >= self._max_value:
                    return False

        return True

    def _is_in_bounds_vectorized(self, values):
        """Vectorized bounds checking for numpy arrays."""
        result = np.ones(values.shape, dtype=bool)

        # Check minimum bound
        if np.isfinite(self._min_value):
            if self._min_inclusive:
                result &= values >= self._min_value
            else:
                result &= values > self._min_value

        # Check maximum bound
        if np.isfinite(self._max_value):
            if self._max_inclusive:
                result &= values <= self._max_value
            else:
                result &= values < self._max_value

        return result

    def _get_bounds_str(self):
        """Get string representation of bounds."""
        left = '[' if self._min_inclusive else '('
        right = ']' if self._max_inclusive else ')'

        min_str = str(self._min_value) if np.isfinite(self._min_value) else '-∞'
        max_str = str(self._max_value) if np.isfinite(self._max_value) else '∞'

        return f'{left}{min_str}, {max_str}{right}'


class BoundedFloat(InexactNumber):
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

    __slots__ = ('_min_value', '_max_value', '_min_inclusive', '_max_inclusive')

    def __init__(self, *, dtype: type[float | np.float64] = float):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (float, np.float64, np.float32):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._min_value = float('-inf')
        self._max_value = float('inf')
        self._min_inclusive = True
        self._max_inclusive = True

    def min(self, value, *, inclusive: bool = True):
        """Set minimum bound. Supports +/- infinity."""
        self._min_value = value
        self._min_inclusive = inclusive
        return self

    def max(self, value, *, inclusive: bool = True):
        """Set maximum bound. Supports +/- infinity."""
        self._max_value = value
        self._max_inclusive = inclusive
        return self

    def convertible_from(self, other):
        if other in (float, np.float64, np.float32, np.float16):
            return True
        return False

    def normalize(self, value, **kwargs):
        normalized_value = super().normalize(value, **kwargs)

        if normalized_value is None:
            return normalized_value

        # Handle arrays
        if isinstance(normalized_value, (list, np.ndarray)):
            if isinstance(normalized_value, np.ndarray):
                # Check for NaN values and values outside bounds
                valid_mask = ~np.isnan(normalized_value)
                if np.any(valid_mask):
                    valid_values = normalized_value[valid_mask]
                    if not np.all(self._is_in_bounds_vectorized(valid_values)):
                        min_val = np.min(valid_values)
                        max_val = np.max(valid_values)
                        bounds = self._get_bounds_str()
                        raise ValueError(
                            f'All non-NaN values must be in {bounds}, got range [{min_val}, {max_val}]'
                        )
            else:  # list
                valid_values = [
                    v
                    for v in normalized_value
                    if not (isinstance(v, float) and np.isnan(v))
                ]
                if valid_values:
                    for v in valid_values:
                        if not self._is_in_bounds(v):
                            min_val = min(valid_values)
                            max_val = max(valid_values)
                            bounds = self._get_bounds_str()
                            raise ValueError(
                                f'All non-NaN values must be in {bounds}, got range [{min_val}, {max_val}]'
                            )
        else:
            # Handle scalars
            if not (isinstance(normalized_value, float) and np.isnan(normalized_value)):
                if not self._is_in_bounds(normalized_value):
                    bounds = self._get_bounds_str()
                    raise ValueError(
                        f'Value must be in {bounds}, got {normalized_value}'
                    )

        return normalized_value

    def _is_in_bounds(self, value):
        """Check if a single value is within bounds."""
        # Check minimum bound
        if np.isfinite(self._min_value):
            if self._min_inclusive:
                if value < self._min_value:
                    return False
            else:
                if value <= self._min_value:
                    return False

        # Check maximum bound
        if np.isfinite(self._max_value):
            if self._max_inclusive:
                if value > self._max_value:
                    return False
            else:
                if value >= self._max_value:
                    return False

        return True

    def _is_in_bounds_vectorized(self, values):
        """Vectorized bounds checking for numpy arrays."""
        result = np.ones(values.shape, dtype=bool)

        # Check minimum bound
        if np.isfinite(self._min_value):
            if self._min_inclusive:
                result &= values >= self._min_value
            else:
                result &= values > self._min_value

        # Check maximum bound
        if np.isfinite(self._max_value):
            if self._max_inclusive:
                result &= values <= self._max_value
            else:
                result &= values < self._max_value

        return result

    def _get_bounds_str(self):
        """Get string representation of bounds."""
        left = '[' if self._min_inclusive else '('
        right = ']' if self._max_inclusive else ')'

        min_str = str(self._min_value) if np.isfinite(self._min_value) else '-∞'
        max_str = str(self._max_value) if np.isfinite(self._max_value) else '∞'

        return f'{left}{min_str}, {max_str}{right}'


# Convenience aliases for common use cases
StrictlyPositiveInt = lambda: BoundedInt().min(1)  # >= 1 integers
PositiveInt = lambda: BoundedInt().min(0)  # >= 0 integers (non-negative)
StrictlyPositiveFloat = lambda: BoundedFloat().min(0, inclusive=False)  # > 0 floats
PositiveFloat = lambda: BoundedFloat().min(0)  # >= 0 floats (non-negative)
UnitFloat = lambda: BoundedFloat().min(0).max(1)  # [0, 1] floats
