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
from typing import Any

import numpy as np
from nomad.metainfo.data_type import ExactNumber, InexactNumber

# Match patterns like '[0,3)', '(0,5]', '[1,)', '(,10)', etc.
bounds_patt = re.compile(r'^([\[\(])(-?\d*\.?\d*|),\s*(-?\d*\.?\d*|)([\]\)])$')


def _flatten_values(data: Any) -> list[Any]:
    """Returns a list of all scalar values from nested list/array structure."""
    if isinstance(data, np.ndarray):
        return data.flatten().tolist()
    elif isinstance(data, list):
        result = []
        for item in data:
            if isinstance(item, list):
                result.extend(_flatten_values(item))
            else:
                result.append(item)
        return result
    else:
        return [data]


class Bound:
    """
    Bounds checker for numeric values using mathematical interval notation.
    `None` and `NaN` values are allowed and will simply pass the checks.

    Range specification:
        - '[0,1]': Closed interval, 0 ≤ x ≤ 1
        - '(0,1)': Open interval, 0 < x < 1
        - '[0,1)': Half-open interval, 0 ≤ x < 1
        - '[1,)': Lower bounded, x ≥ 1
        - '(,10]': Upper bounded, x ≤ 10
        - '': Unbounded (-∞, ∞)
    """

    __slots__ = (
        '_min_value',
        '_max_value',
        '_min_inclusive',
        '_max_inclusive',
        '_original_min_str',
        '_original_max_str',
    )

    def __init__(self, range_str: str = ''):
        """Initialize bounds from range string.

        Args:
            range_str: Range specification like '[0,1]', '(0,)', etc. Empty means unbounded.
        """
        min_val, max_val, min_inc, max_inc, min_str, max_str = self._parse_range(
            range_str
        )
        self._min_value = min_val
        self._max_value = max_val
        self._min_inclusive = min_inc
        self._max_inclusive = max_inc
        self._original_min_str = min_str
        self._original_max_str = max_str

    def _parse_range(self, range_str: str) -> tuple[float, float, bool, bool, str, str]:
        """Parse range string like '[0,3)' into (min_val, max_val, min_inc, max_inc, min_str, max_str)."""
        if not range_str.strip():
            return float('-inf'), float('inf'), False, False, '', ''

        match = bounds_patt.match(range_str.strip())

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

        return min_val, max_val, min_inclusive, max_inclusive, min_str, max_str

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

    def check(self, value: Any, **kwargs) -> Any:
        """Check if value(s) are within bounds. Handles both scalar and array values.

        Note: NaN values will pass bounds checking since NaN comparisons always return False.

        Args:
            value: Value or array to check
            **kwargs: Additional arguments (for compatibility)

        Returns:
            The input value if valid

        Raises:
            ValueError: If any values are outside the bounds
        """
        if value is None:
            return value

        if flat_values := _flatten_values(value):
            invalid_values = [v for v in flat_values if not self._check_single_value(v)]

            if invalid_values:
                min_val = min(flat_values)
                max_val = max(flat_values)
                raise ValueError(
                    f'All values must be in {self}, got range [{min_val}, {max_val}]'
                )

        return value

    def __repr__(self) -> str:
        """Get string representation of bounds."""
        left = '[' if self._min_inclusive else '('
        right = ']' if self._max_inclusive else ')'

        min_str = self._original_min_str if np.isfinite(self._min_value) else ''
        max_str = self._original_max_str if np.isfinite(self._max_value) else ''

        return f'{left}{min_str},{max_str}{right}'


class m_int_bounded(ExactNumber):
    """
    Bounded integer data type.

    Example:
        m_int_bounded(dtype=int, bound=Bound('[1,10]'))    # 1 ≤ x ≤ 10 (integers)
    """

    __slots__ = ('bound',)

    def __init__(self, dtype=int, bound=None):
        """Initialize bounded integer with dtype and bounds.

        Args:
            dtype: Integer data type, mostly used to specify framework and accuracy (int, np.int32, etc.)
            bound: Bound instance specifying the valid range
        """
        super().__init__(dtype)
        self.bound = bound or Bound()

    def convertible_from(self, other):
        """Check if this data type can convert from another type."""
        # Follow the same convertibility rules as the base dtype
        if self._dtype in {int, np.int64}:
            return other in (int, np.int64, np.int32, np.int16, np.int8)
        elif self._dtype is np.int32:
            return other in (np.int32, np.int16, np.int8)
        elif self._dtype is np.int16:
            return other in (np.int16, np.int8)
        elif self._dtype is np.int8:
            return other is np.int8
        else:
            return False

    def serialize_self(self):
        """Serialize the datatype configuration."""
        return super().serialize_self() | {'type_bound': str(self.bound)}

    def normalize_flags(self, flags: dict):
        """Reconstruct from serialized data."""
        bounds_str = flags.get('type_bound', '')
        self.bound = Bound(bounds_str)
        # Apply any flags to base datatype
        super().normalize_flags(flags)
        return self

    def normalize(self, value, **kwargs):
        """Normalize value and validate bounds."""
        normalized_value = super().normalize(value, **kwargs)
        return self.bound.check(normalized_value, **kwargs)

    def standard_type(self):
        """Return the equivalent python type for indexing."""
        return 'int'


class m_float_bounded(InexactNumber):
    """
    Bounded float data type.

    Example:
        m_float_bounded(dtype=float, bound=Bound('[0.0,1.0]'))    # 0.0 ≤ x ≤ 1.0 (floats)
    """

    __slots__ = ('bound',)

    def __init__(self, dtype=float, bound=None):
        """Initialize bounded float with dtype and bounds.

        Args:
            dtype: Float data type, mostly used to specify framework and accuracy (float, np.float64, etc.)
            bound: Bound instance specifying the valid range
        """
        super().__init__(dtype)
        self.bound = bound or Bound()

    def convertible_from(self, other):
        """Check if this data type can convert from another type."""
        # Follow the same convertibility rules as the base dtype
        if self._dtype in {float, np.float64}:
            return other in (float, np.float64, np.float32, np.float16)
        elif self._dtype is np.float32:
            return other in (np.float32, np.float16)
        elif self._dtype is np.float16:
            return other is np.float16
        else:
            return False

    def serialize_self(self):
        """Serialize the datatype configuration."""
        return super().serialize_self() | {'type_bound': str(self.bound)}

    def normalize_flags(self, flags: dict):
        """Reconstruct from serialized data."""
        bounds_str = flags.get('type_bound', '')
        self.bound = Bound(bounds_str)
        # Apply any flags to base datatype
        super().normalize_flags(flags)
        return self

    def normalize(self, value, **kwargs):
        """Normalize value and validate bounds."""
        normalized_value = super().normalize(value, **kwargs)
        return self.bound.check(normalized_value, **kwargs)

    def standard_type(self):
        """Return the equivalent python type for indexing."""
        return 'float'


# Convenience factory functions for common use cases
def strictly_positive_int(*, dtype=int) -> m_int_bounded:
    """Create strictly positive integer type (x ≥ 1)."""
    return m_int_bounded(dtype=dtype, bound=Bound('[1,)'))


def positive_int(*, dtype=int) -> m_int_bounded:
    """Create positive integer type (x ≥ 0)."""
    return m_int_bounded(dtype=dtype, bound=Bound('[0,)'))


def strictly_positive_float(*, dtype=float) -> m_float_bounded:
    """Create strictly positive float type (x > 0)."""
    return m_float_bounded(dtype=dtype, bound=Bound('(0,)'))


def positive_float(*, dtype=float) -> m_float_bounded:
    """Create positive float type (x ≥ 0)."""
    return m_float_bounded(dtype=dtype, bound=Bound('[0,)'))


def unit_float(*, dtype=float) -> m_float_bounded:
    """Create unit interval float type (0 ≤ x ≤ 1)."""
    return m_float_bounded(dtype=dtype, bound=Bound('[0,1]'))
