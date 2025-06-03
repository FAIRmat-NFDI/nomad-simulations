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

import re
from collections.abc import Generator
from typing import Any

import numpy as np
from nomad.metainfo.data_type import Datatype, normalize_type


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


class Bound:
    """
    Bounds checker for numeric values using mathematical interval notation.

    Range specification:
        - '[0,1]': Closed interval, 0 ≤ x ≤ 1
        - '(0,1)': Open interval, 0 < x < 1
        - '[0,1)': Half-open interval, 0 ≤ x < 1
        - '[1,)': Lower bounded, x ≥ 1
        - '(,10]': Upper bounded, x ≤ 10
        - '': Unbounded (-∞, ∞)
    """

    __slots__ = ('_min_value', '_max_value', '_min_inclusive', '_max_inclusive')

    def __init__(self, range_str: str = ''):
        """Initialize bounds from range string.

        Args:
            range_str: Range specification like '[0,1]', '(0,)', etc. Empty means unbounded.
        """
        min_val, max_val, min_inc, max_inc = self._parse_range(range_str)
        self._min_value = min_val
        self._max_value = max_val
        self._min_inclusive = min_inc
        self._max_inclusive = max_inc

    def _parse_range(self, range_str: str) -> tuple[float, float, bool, bool]:
        """Parse range string like '[0,3)' into (min_val, max_val, min_inc, max_inc)."""
        if not range_str.strip():
            return float('-inf'), float('inf'), False, False

        # Match patterns like '[0,3)', '(0,5]', '[1,)', '(,10)', etc.
        pattern = r'^([\[\(])(-?\d*\.?\d*|),\s*(-?\d*\.?\d*|)([\]\)])$'
        match = re.match(pattern, range_str.strip())

        if not match:
            raise ValueError(
                f"Invalid range format: '{range_str}'. "
                f"Expected format like '[0,3)', '(0,5]', '[1,)', '(,10)', etc."
            )

        left_bracket, min_str, max_str, right_bracket = match.groups()

        # Parse bounds (empty means infinity)
        min_val = float('-inf') if not min_str else float(min_str)
        max_val = float('inf') if not max_str else float(max_str)

        # Parse inclusivity
        min_inclusive = left_bracket == '[' and bool(min_str)
        max_inclusive = right_bracket == ']' and bool(max_str)

        return min_val, max_val, min_inclusive, max_inclusive

    def _check_single_value(self, value: int | float) -> bool:
        """Check if a single value is within the specified bounds."""
        # lower bound
        if np.isfinite(self._min_value):
            if self._min_inclusive:
                if value < self._min_value:
                    return False
            else:
                if value <= self._min_value:
                    return False

        # upper bound
        if np.isfinite(self._max_value):
            if self._max_inclusive:
                if value > self._max_value:
                    return False
            else:
                if value >= self._max_value:
                    return False

        return True

    def check(self, value: Any, *, filter_nan: bool = False) -> None:
        """Check if value(s) are within bounds. Raise ValueError if not.

        Args:
            value: Value or array to check
            filter_nan: If True, ignore NaN values in validation
        """
        if value is None:
            return

        flat_values = list(_flatten_values(value))

        # Filter NaN values if requested
        if filter_nan:
            valid_values = [
                v for v in flat_values if not (isinstance(v, float) and np.isnan(v))
            ]
        else:
            valid_values = flat_values

        if valid_values:
            invalid_values = [
                v for v in valid_values if not self._check_single_value(v)
            ]

            if invalid_values:
                min_val = min(valid_values)
                max_val = max(valid_values)
                bounds_str = self.get_bounds_str()
                error_prefix = 'All non-NaN values' if filter_nan else 'All values'
                raise ValueError(
                    f'{error_prefix} must be in {bounds_str}, got range [{min_val}, {max_val}]'
                )

    def get_bounds_str(self) -> str:
        """Get string representation of bounds."""
        left = '[' if self._min_inclusive else '('
        right = ']' if self._max_inclusive else ')'

        min_str = str(self._min_value) if np.isfinite(self._min_value) else '-∞'
        max_str = str(self._max_value) if np.isfinite(self._max_value) else '∞'

        return f'{left}{min_str}, {max_str}{right}'

    def __repr__(self) -> str:
        return f'Bound({self.get_bounds_str()!r})'


class BoundedNumber:
    """
    Bounded numeric data type that coordinates between NOMAD's dtype system and bounds checking.

    Delegates type normalization to NOMAD's existing data types (m_int32, m_float64, etc.)
    and bounds validation to a Bound instance.

    Example:
        BoundedNumber(dtype='m_int32', bounds=Bound('[1,10]'))    # 1 ≤ x ≤ 10 (32-bit integers)
    """

    __slots__ = ('_base_datatype', '_bounds')

    def __init__(self, *, dtype: str | type | Datatype, bounds: Bound):
        """Initialize bounded number with NOMAD dtype and bounds.

        Args:
            dtype: NOMAD data type (e.g., 'm_int32', 'm_float64', int, float) or Datatype instance
            bounds: Bound instance specifying the valid range
        """
        # Normalize the dtype using NOMAD's system
        if isinstance(dtype, Datatype):
            self._base_datatype = dtype
        else:
            self._base_datatype = normalize_type(dtype)

        self._bounds = bounds

    def convertible_from(self, other: Any) -> bool:
        """Check if this data type can convert from another type."""
        return self._base_datatype.convertible_from(other)

    def normalize(self, value: Any, **kwargs: Any) -> Any:
        """Normalize value using base datatype and validate bounds."""
        normalized_value = self._base_datatype.normalize(value, **kwargs)

        # Check if this is a float type for NaN filtering
        datatype_name = self._base_datatype.__class__.__name__.lower()
        filter_nan = 'float' in datatype_name or 'inexact' in datatype_name

        self._bounds.check(normalized_value, filter_nan=filter_nan)
        return normalized_value

    def serialize_self(self):
        """Serialize the datatype configuration."""
        return self._base_datatype.serialize_self()

    @property
    def _dtype(self):
        """Get the underlying dtype."""
        return getattr(self._base_datatype, '_dtype', None)

    def __repr__(self):
        dtype_name = self._base_datatype.__class__.__name__
        return (
            f'{self.__class__.__name__}(dtype="{dtype_name}", bounds={self._bounds!r})'
        )


# Convenience factory functions for common use cases
def bounded_int(
    *, dtype: str | type | Datatype = 'm_int32', bounds: Bound
) -> BoundedNumber:
    """Create a bounded integer datatype."""
    return BoundedNumber(dtype=dtype, bounds=bounds)


def bounded_float(
    *, dtype: str | type | Datatype = 'm_float64', bounds: Bound
) -> BoundedNumber:
    """Create a bounded float datatype."""
    return BoundedNumber(dtype=dtype, bounds=bounds)


def strictly_positive_int(*, dtype: str | type | Datatype = 'm_int32') -> BoundedNumber:
    """Create strictly positive integer type (x ≥ 1)."""
    return BoundedNumber(dtype=dtype, bounds=Bound('[1,)'))


def positive_int(*, dtype: str | type | Datatype = 'm_int32') -> BoundedNumber:
    """Create positive integer type (x ≥ 0)."""
    return BoundedNumber(dtype=dtype, bounds=Bound('[0,)'))


def strictly_positive_float(
    *, dtype: str | type | Datatype = 'm_float64'
) -> BoundedNumber:
    """Create strictly positive float type (x > 0)."""
    return BoundedNumber(dtype=dtype, bounds=Bound('(0,)'))


def positive_float(*, dtype: str | type | Datatype = 'm_float64') -> BoundedNumber:
    """Create positive float type (x ≥ 0)."""
    return BoundedNumber(dtype=dtype, bounds=Bound('[0,)'))


def unit_float(*, dtype: str | type | Datatype = 'm_float64') -> BoundedNumber:
    """Create unit interval float type (0 ≤ x ≤ 1)."""
    return BoundedNumber(dtype=dtype, bounds=Bound('[0,1]'))
