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

import builtins
import re
from typing import Any

import numpy as np
from nomad.metainfo.data_type import ExactNumber, InexactNumber
from nomad.utils import get_logger

# Used only by the soft ('log') out-of-bounds mode, which has no bound logger at
# assignment time; the owning `section` (when available) is added as context.
LOGGER = get_logger(__name__)

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

    Two intervals are referred to throughout: the *core interval* is the declared
    interval `[lower, upper]` itself; the *slack band* is that interval widened by
    `slack` on both ends, `[lower - slack, upper + slack]`. A value is accepted if it
    is in the core interval or the slack band; anything beyond the slack band is a
    violation.

    The two encode different intents. The core interval is the **physically meaningful
    range** the quantity must lie in (e.g. an occupation in `[0, 2]`, a non-negative
    DOS). `slack` is **not** a widening of that range; it only absorbs **numerical
    discrepancies** -- floating-point round-off and finite-precision output that push a
    value a hair outside the interval -- so such noise is tolerated instead of aborting
    processing. Keep `slack` at the scale of that noise, never large enough to admit a
    physically distinct value.

    Units:
        Bounds and slack are plain magnitudes expressed **in the owning quantity's
        declared unit**. The check is applied to the value's magnitude *as assigned*
        (for a `flexible_unit` quantity the magnitude is not converted first; any
        storage conversion to the declared unit happens afterward). Write the interval
        and `slack` in the same unit you declared on the quantity (e.g. for a
        `unit='joule'` quantity, `slack=1e-3` means 1 mJ). For a dimensionless quantity
        (e.g. an occupation) they are pure numbers.

        Because a `flexible_unit=True` quantity is checked in whatever unit each value
        is assigned in, only *scale-invariant* bounds are meaningful there: pure sign
        constraints whose finite endpoints are exactly 0 (`positive_float`,
        `strictly_positive_float`) and no slack. A nonzero finite endpoint or a positive
        `slack` is scale-dependent -- it means something different in J than in mJ (the
        same physical value passes in one unit and fails in another) -- and is rejected
        on first assignment (see `is_scale_invariant` and the bounded types' `normalize`).

    Optional tolerance and failure handling:
        - `slack`: **absolute** (not relative) tolerance defining the slack band, in the
          declared unit (see Units above), sized to absorb numerical discrepancies
          (floating-point noise) at the interval edges rather than to widen the
          physically meaningful range. Defaults to `0.0` (band == core interval, i.e. the
          exact historical behavior).
        - `on_violation`: what to do for values beyond the slack band, `'raise'`
          (default: raise `ValueError`, the historical behavior) or `'log'` (emit a
          warning and keep the value -- unless `clamp` also coerces it -- so a negligible
          excursion does not abort processing).
        - `clamp`: when `True`, any value *outside the core interval* is snapped onto the
          nearest endpoint of `[lower, upper]`; core values pass through untouched. `slack`
          and `clamp` are orthogonal: `slack` decides only whether a value is a *violation*,
          `clamp` decides what happens to out-of-core values that are **not raised** -- so
          under the default `'raise'` only slack-accepted values are ever clamped (anything
          beyond the band raises first), while under `'log'` beyond-band values are clamped
          too rather than kept. Every *finite* endpoint must therefore be inclusive
          (infinite sides are allowed; validated in `__init__`), so clamp never snaps onto
          an excluded open endpoint.
    """

    __slots__ = (
        '_min_value',
        '_max_value',
        '_min_inclusive',
        '_max_inclusive',
        '_original_min_str',
        '_original_max_str',
        'slack',
        'on_violation',
        'clamp',
    )

    def __init__(
        self,
        range_str: str = '',
        *,
        slack: float = 0.0,
        on_violation: str = 'raise',
        clamp: bool = False,
    ):
        """Initialize bounds from range string.

        Args:
            range_str: Range specification like '[0,1]', '(0,)', etc. Empty means unbounded.
            slack: Non-negative absolute tolerance widening the acceptance region, in the
                owning quantity's declared unit (see the class docstring's Units section).
            on_violation: `'raise'` or `'log'` handling for out-of-region values.
            clamp: Coerce any out-of-core value into the interval; `slack` only sets the
                violation threshold, not what gets snapped.
        """
        if slack < 0:
            raise ValueError(f'slack must be non-negative, got {slack}')
        if on_violation not in ('raise', 'log'):
            raise ValueError(
                f"on_violation must be 'raise' or 'log', got {on_violation!r}"
            )
        min_val, max_val, min_inc, max_inc, min_str, max_str = self._parse_range(
            range_str
        )
        self._min_value = min_val
        self._max_value = max_val
        self._min_inclusive = min_inc
        self._max_inclusive = max_inc
        self._original_min_str = min_str
        self._original_max_str = max_str
        self.slack = float(slack)
        self.on_violation = on_violation
        self.clamp = bool(clamp)
        # Clamp snaps to the raw endpoints, so an exclusive finite bound would be
        # coerced to a value the interval itself rejects. Require every finite endpoint
        # to be inclusive (infinite sides are fine -- clamp never snaps to +/-inf).
        if self.clamp and (
            (np.isfinite(min_val) and not min_inc)
            or (np.isfinite(max_val) and not max_inc)
        ):
            raise ValueError(
                f'clamp=True requires every finite endpoint to be inclusive (infinite '
                f'sides allowed); {self} has an exclusive finite endpoint it could snap to.'
            )

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

    def _within_slack_band(self, value: int | float) -> bool:
        """Whether a value lies within the slack band `[min-slack, max+slack]`."""
        if np.isfinite(self._min_value) and value < self._min_value - self.slack:
            return False
        if np.isfinite(self._max_value) and value > self._max_value + self.slack:
            return False
        return True

    def _is_acceptable(self, value: int | float) -> bool:
        """Whether a value is accepted: it satisfies the core interval, or (with a
        positive `slack`) falls within the slack band."""
        if self._check_single_value(value):
            return True
        # This is not a second core-interval check: at slack == 0 the band collapses to
        # the *inclusive* core edges and would re-admit the endpoints an open interval
        # rejects, so only consult the band once slack adds real width.
        return self.slack > 0 and self._within_slack_band(value)

    def _clamp_single(self, value: int | float) -> int | float:
        """Snap one scalar into `[lower, upper]`: below the lower bound -> lower, above the
        upper bound -> upper. Core-valid values, infinite-side bounds, and NaN pass
        through unchanged."""
        if np.isfinite(self._min_value) and value < self._min_value:
            return self._min_value
        if np.isfinite(self._max_value) and value > self._max_value:
            return self._max_value
        return value

    def _apply_clamp(self, value: Any) -> Any:
        """Coerce every out-of-core entry of `value` into `[lower, upper]`, preserving
        structure (scalar / list / ndarray). Clamp governs coercion into range; `slack`
        governs only whether an entry is a violation (raise/log), not whether it is
        snapped -- so a beyond-band entry is clamped here too, not left out of range.

        `np.where` (rather than in-place assignment) is used for arrays so a fractional
        bound promotes an integer array to float instead of truncating the snapped value
        back outside the interval; this matches the scalar path, which returns the float
        bound directly."""
        if isinstance(value, np.ndarray):
            arr = value
            if np.isfinite(self._min_value):
                arr = np.where(arr < self._min_value, self._min_value, arr)
            if np.isfinite(self._max_value):
                arr = np.where(arr > self._max_value, self._max_value, arr)
            return arr
        if isinstance(value, list):
            return [self._apply_clamp(v) for v in value]
        return self._clamp_single(value)

    def _log_violation(self, violations: list, section: Any) -> None:
        """Emit a single warning for values beyond the slack band, enriched with `section`
        context when available (no bound logger exists at assignment time). The
        `disposition` field records what then happens to those values: `'clamped'` into
        range when `clamp` is set, otherwise `'kept'` as-is."""
        context: dict[str, Any] = {}
        if section is not None:
            m_def = getattr(section, 'm_def', None)
            context['section'] = (
                m_def.name if m_def is not None else type(section).__name__
            )
            try:
                context['path'] = section.m_path()
            except Exception:
                # section not yet attached to an archive; omit the path field
                pass
        # Report the range of the offending values only; `violations` excludes NaN
        # (which is acceptable), so plain min/max cannot be poisoned to NaN.
        LOGGER.warning(
            'Value(s) outside bounds.',
            disposition='clamped' if self.clamp else 'kept',
            bound=str(self),
            slack=self.slack,
            n_violations=len(violations),
            value_range=[min(violations), max(violations)],
            **context,
        )

    def check(self, value: Any, **kwargs) -> Any:
        """Check if value(s) are within bounds. Handles both scalar and array values.

        Values within the core interval or the slack band are accepted. Values beyond the
        slack band either raise `ValueError` (`on_violation='raise'`, the default) or are
        logged (`on_violation='log'`), using the `section` kwarg for context when present.
        When `clamp` is set, every out-of-core value (slack-accepted or, in `'log'` mode,
        beyond-band) is finally snapped into `[lower, upper]`.

        Note: NaN values pass bounds checking since NaN comparisons always return False.

        Args:
            value: Value or array to check.
            **kwargs: Additional arguments; `section` (the owning `MSection`) is used
                for log context when provided by the metainfo framework.

        Returns:
            The input value (possibly clamped) if accepted or logged.

        Raises:
            ValueError: If any values are beyond the slack band and `on_violation='raise'`.
        """
        if value is None:
            return value

        if flat_values := _flatten_values(value):
            violations = [v for v in flat_values if not self._is_acceptable(v)]

            if violations:
                if self.on_violation == 'raise':
                    min_val = min(flat_values)
                    max_val = max(flat_values)
                    slack_note = f' (±{self.slack})' if self.slack > 0 else ''
                    raise ValueError(
                        f'All values must be in {self}{slack_note}, '
                        f'got range [{min_val}, {max_val}]'
                    )
                self._log_violation(violations, kwargs.get('section'))

        # Runs whether or not there were violations: snaps slack-accepted values (and, in
        # log mode, kept beyond-band ones) into the core interval; a no-op if none exist.
        if self.clamp:
            return self._apply_clamp(value)
        return value

    def is_scale_invariant(self) -> bool:
        """Whether this bound survives an unknown positive unit rescale, and is therefore
        meaningful on a `flexible_unit` quantity. True only for a pure sign constraint:
        every finite endpoint is exactly 0 and there is no absolute `slack` (a nonzero
        endpoint or positive slack means something different across units)."""
        if self.slack > 0:
            return False
        if np.isfinite(self._min_value) and self._min_value != 0:
            return False
        if np.isfinite(self._max_value) and self._max_value != 0:
            return False
        return True

    def __repr__(self) -> str:
        """Get string representation of bounds."""
        left = '[' if self._min_inclusive else '('
        right = ']' if self._max_inclusive else ')'

        min_str = self._original_min_str if np.isfinite(self._min_value) else ''
        max_str = self._original_max_str if np.isfinite(self._max_value) else ''

        return f'{left}{min_str},{max_str}{right}'


def _serialize_bounded_type(cls: type, dtype: type, bound: Bound, flags: dict) -> dict:
    """Serialize the bounded type as `type_kind='custom'` so `normalize_type` reloads this
    exact class (with its bound) rather than the plain base numeric type; `dtype` goes in
    `type_dtype`. Inverse of `_deserialize_bounded_type`."""
    # `type_kind='custom'` is the discriminator that reloads this class, not a plain dtype.
    return {
        'type_kind': 'custom',
        'type_data': f'{cls.__module__}.{cls.__name__}',
        'type_dtype': dtype.__name__,
        'type_bound': str(bound),
        'type_bound_slack': bound.slack,
        'type_bound_on_violation': bound.on_violation,
        'type_bound_clamp': bound.clamp,
    } | flags


def _resolve_dtype_name(dtype_name: str) -> type:
    """Resolve a serialized `type_dtype` name (`'int'`, `'float64'`, ...) to its numeric
    type, checking `builtins` then `numpy`. Raise `ValueError` with context if the name is
    unknown or resolves to a non-type object (e.g. `'array'`, `'sum'` -> a numpy function),
    so a corrupted or alien archive fails actionably here instead of silently mis-typing
    downstream."""
    resolved = getattr(builtins, dtype_name, None)
    if resolved is None:
        resolved = getattr(np, dtype_name, None)
    if not isinstance(resolved, type):
        raise ValueError(
            f'unknown dtype {dtype_name!r} in serialized bounded type: not a numeric type '
            'on builtins or numpy'
        )
    return resolved


def _deserialize_bounded_type(flags: dict) -> tuple[type | None, Bound]:
    """Reconstruct `(dtype, bound)` from serialized `flags`, the inverse of
    `_serialize_bounded_type`; `dtype` is `None` when absent, keeping the constructor
    default. Every field is read via `flags.get(key, <default>)`, so missing keys fall
    back to defaults -- a deliberate leniency: production should conditionally extend the
    payload (dropping default-valued `type_bound_*` knobs to avoid archive churn), and
    default-filling keeps that backward-safe. Confirm the direction with the schema
    maintainers first. On every serialization bump, add the new emitted shape as a case to
    `test_deserialize_tolerates_serialization_variants` so older archives stay readable."""
    dtype: type | None = None
    if (dtype_name := flags.get('type_dtype')) is not None:
        dtype = _resolve_dtype_name(dtype_name)
    bound = Bound(
        flags.get('type_bound', ''),
        slack=flags.get('type_bound_slack', 0.0),
        on_violation=flags.get('type_bound_on_violation', 'raise'),
        clamp=flags.get('type_bound_clamp', False),
    )
    return dtype, bound


def _reject_scale_dependent_flexible_unit(flexible_unit: bool, bound: Bound) -> None:
    """Raise if a scale-dependent `bound` is used on a `flexible_unit` quantity. Called
    from `normalize` on first assignment, the earliest point `flexible_unit` is resolved
    on the definition (it is not yet set when the datatype is attached).

    Limitation: this catches *multiplicative* scale-dependence only. Offset (affine) units
    -- Celsius, Fahrenheit, Reaumur -- slip through and cannot be caught here, because
    nomad strips the unit (`value.m`) in `Quantity.__set__` before `normalize` runs, so the
    datatype only ever sees the bare magnitude. Thus `-10 degC` (a valid 263 K) is tested
    as `-10` and wrongly fails a positivity bound; a proper fix needs a nomad-core hook at
    the metainfo layer. Tracked by the xfail
    `test_offset_unit_on_flexible_unit_is_scale_shifted`."""
    if flexible_unit and not bound.is_scale_invariant():
        raise ValueError(
            f'A scale-dependent bound ({bound}, slack={bound.slack}) is '
            'ill-defined on a flexible_unit quantity, whose values are checked in '
            'their assigned unit without conversion. Use a sign-only bound (e.g. '
            'positive_float / strictly_positive_float) or drop flexible_unit.'
        )


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

    def serialize_self(self) -> dict:
        return _serialize_bounded_type(
            self.__class__, self._dtype, self.bound, self.flags
        )

    def normalize_flags(self, flags: dict):
        dtype, self.bound = _deserialize_bounded_type(flags)
        if dtype is not None:
            # `_dtype` is an inherited slot from `Primitive`; mypy cannot see it across
            # the silently-followed nomad import, hence the scoped ignore.
            self._dtype = dtype  # type: ignore[misc]
        super().normalize_flags(flags)
        return self

    def normalize(self, value, **kwargs):
        _reject_scale_dependent_flexible_unit(self.flexible_unit, self.bound)
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

    def serialize_self(self) -> dict:
        return _serialize_bounded_type(
            self.__class__, self._dtype, self.bound, self.flags
        )

    def normalize_flags(self, flags: dict):
        dtype, self.bound = _deserialize_bounded_type(flags)
        if dtype is not None:
            # `_dtype` is an inherited slot from `Primitive`; mypy cannot see it across
            # the silently-followed nomad import, hence the scoped ignore.
            self._dtype = dtype  # type: ignore[misc]
        super().normalize_flags(flags)
        return self

    def normalize(self, value, **kwargs):
        _reject_scale_dependent_flexible_unit(self.flexible_unit, self.bound)
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
