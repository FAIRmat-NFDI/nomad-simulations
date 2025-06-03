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
from typing import Any, Callable

import numpy as np
from nomad.metainfo.data_type import Datatype, normalize_type


def _parse_range(range_str: str) -> tuple[float, float, bool, bool]:
    """Parse range string like '[0,3)' into (min_val, max_val, min_inc, max_inc).

    Args:
        range_str: Range specification like '[0,3)', '(0,5]', '[1,)', '(,10)', etc.
                  Empty string means unbounded (-∞, ∞)

    Returns:
        Tuple of (min_value, max_value, min_inclusive, max_inclusive)
    """
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
    value: int | float,
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


class BoundedNumber:
    """
    Bounded numeric data type with configurable ranges using NOMAD's type system.

    Delegates to NOMAD's existing data types (m_int32, m_float64, etc.) for normalization
    and conversion, adding bounds validation on top.

    Range specification:
        - '[0,1]': Closed interval, 0 ≤ x ≤ 1
        - '(0,1)': Open interval, 0 < x < 1
        - '[0,1)': Half-open interval, 0 ≤ x < 1
        - '[1,)': Lower bounded, x ≥ 1
        - '(,10]': Upper bounded, x ≤ 10
        - '': Unbounded (-∞, ∞) with non-inclusive bounds

    Example:
        BoundedNumber(dtype='m_int32', range='[1,10]')    # 1 ≤ x ≤ 10 (32-bit integers)
    """

    __slots__ = (
        '_min_value',
        '_max_value',
        '_min_inclusive',
        '_max_inclusive',
        '_base_datatype',
        '_error_message_prefix',
    )

    def __init__(self, *, dtype: str | type | Datatype, range: str = ''):
        """Initialize bounded number with NOMAD dtype and optional range.

        Args:
            dtype: NOMAD data type (e.g., 'm_int32', 'm_float64', int, float) or Datatype instance
            range: Range specification like '[0,1]', '(0,)', etc. Empty means unbounded.
        """
        # Normalize the dtype using NOMAD's system
        if isinstance(dtype, Datatype):
            self._base_datatype = dtype
        else:
            self._base_datatype = normalize_type(dtype)

        # Determine error message prefix based on datatype
        datatype_name = self._base_datatype.__class__.__name__.lower()
        if 'float' in datatype_name or 'inexact' in datatype_name:
            self._error_message_prefix = 'All non-NaN values'
        else:
            self._error_message_prefix = 'All values'

        # Initialize bounds
        min_val, max_val, min_inc, max_inc = _parse_range(range)
        self._min_value = min_val
        self._max_value = max_val
        self._min_inclusive = min_inc
        self._max_inclusive = max_inc

    def convertible_from(self, other: Any) -> bool:
        """Check if this data type can convert from another type."""
        return self._base_datatype.convertible_from(other)

    def _filter_values_for_validation(self, flat_values: list[Any]) -> list[Any]:
        """Filter values for validation (removes NaN for floats, no filtering for integers)."""
        datatype_name = self._base_datatype.__class__.__name__.lower()
        if 'float' in datatype_name or 'inexact' in datatype_name:
            return [
                v for v in flat_values if not (isinstance(v, float) and np.isnan(v))
            ]
        else:
            return flat_values

    def _validate_bounds(self, normalized_value: Any) -> Any:
        """Validate bounds and return the value on success, raise on failure."""
        if normalized_value is None:
            return None

        flat_values = list(_flatten_values(normalized_value))
        valid_values = self._filter_values_for_validation(flat_values)

        if valid_values:
            invalid_values = [
                v
                for v in valid_values
                if not _check_bounds(
                    v,
                    self._min_value,
                    self._max_value,
                    self._min_inclusive,
                    self._max_inclusive,
                )
            ]

            if invalid_values:
                min_val = min(valid_values)
                max_val = max(valid_values)
                bounds = _get_bounds_str(
                    self._min_value,
                    self._max_value,
                    self._min_inclusive,
                    self._max_inclusive,
                )
                raise ValueError(
                    f'{self._error_message_prefix} must be in {bounds}, got range [{min_val}, {max_val}]'
                )

        return normalized_value

    def normalize(self, value: Any, **kwargs: Any) -> Any:
        """Normalize value using base datatype and validate bounds."""
        return self._validate_bounds(self._base_datatype.normalize(value, **kwargs))

    def serialize_self(self):
        """Serialize the datatype configuration."""
        return self._base_datatype.serialize_self()

    @property
    def _dtype(self):
        """Get the underlying dtype."""
        return getattr(self._base_datatype, '_dtype', None)

    def __repr__(self):
        range_str = _get_bounds_str(
            self._min_value, self._max_value, self._min_inclusive, self._max_inclusive
        )
        dtype_name = self._base_datatype.__class__.__name__
        return f'{self.__class__.__name__}(dtype="{dtype_name}", range="{range_str}")'

    # Keep chainable methods for backwards compatibility
    def min(self, value: int | float, *, inclusive: bool = True) -> 'BoundedNumber':
        """Set minimum bound. Supports +/- infinity."""
        self._min_value = value
        self._min_inclusive = inclusive
        return self

    def max(self, value: int | float, *, inclusive: bool = True) -> 'BoundedNumber':
        """Set maximum bound. Supports +/- infinity."""
        self._max_value = value
        self._max_inclusive = inclusive
        return self


# Convenience aliases for common use cases
StrictlyPositiveInt: Callable[[], BoundedNumber] = lambda: BoundedNumber(
    dtype='m_int32', range='[1,)'
)  # x ≥ 1 integers
PositiveInt: Callable[[], BoundedNumber] = lambda: BoundedNumber(
    dtype='m_int32', range='[0,)'
)  # x ≥ 0 integers
StrictlyPositiveFloat: Callable[[], BoundedNumber] = lambda: BoundedNumber(
    dtype='m_float64', range='(0,)'
)  # x > 0 floats
PositiveFloat: Callable[[], BoundedNumber] = lambda: BoundedNumber(
    dtype='m_float64', range='[0,)'
)  # x ≥ 0 floats
UnitFloat: Callable[[], BoundedNumber] = lambda: BoundedNumber(
    dtype='m_float64', range='[0,1]'
)  # [0, 1] floats

# Backwards compatibility aliases
BoundedInt = BoundedNumber
BoundedFloat = BoundedNumber
