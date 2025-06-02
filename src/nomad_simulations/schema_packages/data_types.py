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


class PositiveInt(ExactNumber):
    """
    Integer data type that only allows positive values (> 0).
    """

    __slots__ = ()

    def __init__(self, *, dtype: type[int | np.int32] = int):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (int, np.int32, np.int64):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._np_base = np.integer

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
                if np.any(normalized_value <= 0):
                    raise ValueError(
                        f'All values must be positive, got array with min value {np.min(normalized_value)}'
                    )
            else:  # list
                if any(v <= 0 for v in normalized_value):
                    min_val = min(normalized_value)
                    raise ValueError(
                        f'All values must be positive, got list with min value {min_val}'
                    )
        else:
            # Handle scalars
            if normalized_value <= 0:
                raise ValueError(f'Value must be positive, got {normalized_value}')

        return normalized_value


class PositiveFloat(InexactNumber):
    """
    Float data type that only allows positive values (> 0).
    """

    __slots__ = ()

    def __init__(self, *, dtype: type[float | np.float64] = float):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (float, np.float64, np.float32):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._np_base = np.inexact

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
                # Check for NaN values and non-positive values
                valid_mask = ~np.isnan(normalized_value)
                if np.any(valid_mask) and np.any(normalized_value[valid_mask] <= 0):
                    min_val = np.min(normalized_value[valid_mask])
                    raise ValueError(
                        f'All non-NaN values must be positive, got array with min value {min_val}'
                    )
            else:  # list
                valid_values = [
                    v
                    for v in normalized_value
                    if not (isinstance(v, float) and np.isnan(v))
                ]
                if valid_values and any(v <= 0 for v in valid_values):
                    min_val = min(valid_values)
                    raise ValueError(
                        f'All non-NaN values must be positive, got list with min value {min_val}'
                    )
        else:
            # Handle scalars
            if (
                not (isinstance(normalized_value, float) and np.isnan(normalized_value))
                and normalized_value <= 0
            ):
                raise ValueError(f'Value must be positive, got {normalized_value}')

        return normalized_value


class UnitFloat(InexactNumber):
    """
    Float data type that only allows values between 0 and 1 (inclusive by default).
    Use .exclude_min() and .exclude_max() to make bounds exclusive.
    """

    __slots__ = ('_min_inclusive', '_max_inclusive')

    def __init__(self, *, dtype: type[float | np.float64] = float):
        if isinstance(dtype, np.dtype):
            dtype = dtype.type

        if dtype not in (float, np.float64, np.float32):
            raise ValueError(f'Invalid dtype for {self.__class__.__name__}.')

        super().__init__(dtype)
        self._np_base = np.inexact
        self._min_inclusive = True
        self._max_inclusive = True

    def exclude_min(self):
        """Make the minimum bound exclusive (> 0 instead of >= 0)."""
        self._min_inclusive = False
        return self

    def exclude_max(self):
        """Make the maximum bound exclusive (< 1 instead of <= 1)."""
        self._max_inclusive = False
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
                    min_check = (
                        valid_values > 0
                        if not self._min_inclusive
                        else valid_values >= 0
                    )
                    max_check = (
                        valid_values < 1
                        if not self._max_inclusive
                        else valid_values <= 1
                    )
                    if not np.all(min_check & max_check):
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
        min_check = value > 0 if not self._min_inclusive else value >= 0
        max_check = value < 1 if not self._max_inclusive else value <= 1
        return min_check and max_check

    def _get_bounds_str(self):
        """Get string representation of bounds."""
        left = '(' if not self._min_inclusive else '['
        right = ')' if not self._max_inclusive else ']'
        return f'{left}0, 1{right}'
