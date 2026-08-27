from unittest.mock import Mock

import numpy as np
import pytest
from nomad.metainfo import Quantity, Section
from nomad.metainfo.data_type import (
    m_float32,
    m_float64,
    m_int16,
    m_int32,
    normalize_type,
)
from nomad.units import ureg

import nomad_simulations.schema_packages.data_types as dt_module
from nomad_simulations.schema_packages.data_types import (
    Bound,
    m_float_bounded,
    m_int_bounded,
)


# Test section class for serialization tests
class TestSection(Section):
    bounded_value = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0,1]')),
        description='A bounded float value',
    )
    bounded_array = Quantity(
        type=m_int_bounded(dtype=int, bound=Bound('[1,10]')),
        shape=['*'],
        description='An array of bounded integers',
    )


# Unit test section class for serialization tests
class TestUnitSerializationSection(Section):
    bounded_quantity = Quantity(
        type=m_float_bounded(dtype=float, bound=Bound('[0,10]')), unit='joule'
    )


# Importable path nomad's `type_kind='custom'` reconstruction resolves for a bounded type.
_M_FLOAT_BOUNDED_PATH = f'{m_float_bounded.__module__}.{m_float_bounded.__name__}'


def setup_datatype_for_testing(datatype_instance, shape=None):
    """Helper function to set up a datatype instance for testing."""
    mock_definition = Mock()
    mock_definition.shape = shape
    mock_definition.unit = None
    mock_definition.flexible_unit = False
    datatype_instance.attach_definition(mock_definition)
    return datatype_instance


class TestBound:
    """Test the Bound class functionality."""

    @pytest.mark.parametrize(
        'range_str,test_values,should_pass',
        [
            ('[0,10]', [0, 5, 10], True),
            ('[0,10]', [-1, 11], False),
            ('(0,10)', [1, 5, 9], True),
            ('(0,10)', [0, 10], False),
            ('[5,)', [5, 100], True),
            ('[5,)', [4], False),
            ('(,10]', [-100, 0, 10], True),
            ('(,10]', [11], False),
        ],
    )
    def test_check_values(self, range_str, test_values, should_pass):
        """Test bounds checking."""
        bound = Bound(range_str)

        if should_pass:
            for value in test_values:
                bound.check(value)  # Should not raise
        else:
            for value in test_values:
                with pytest.raises(ValueError):
                    bound.check(value)

    @pytest.mark.parametrize(
        'test_value,should_pass',
        [
            (float('nan'), True),  # NaN should pass
            ([0.5, float('nan'), 0.8], True),  # Array with NaN should pass
            (None, True),  # None should pass
        ],
    )
    def test_special_values(self, test_value, should_pass):
        """Test handling of special values (NaN, None)."""
        bound = Bound('[0,1]')
        if should_pass:
            bound.check(test_value)  # Should not raise
        else:
            with pytest.raises(ValueError):
                bound.check(test_value)

    @pytest.mark.parametrize(
        'range_str,expected_str,should_pass',
        [
            # Empty bounds
            ('', '(,)', True),
            # Integer bounds
            ('[0,10]', '[0,10]', True),
            ('(0,10)', '(0,10)', True),
            ('[5,)', '[5,)', True),
            ('(,10]', '(,10]', True),
            # Float bounds with different precisions
            ('[0.0,1.0]', '[0.0,1.0]', True),
            ('(0.5,1.5)', '(0.5,1.5)', True),
            ('[0.25,0.75]', '[0.25,0.75]', True),
            # High precision floats
            ('[0.123456,0.987654]', '[0.123456,0.987654]', True),
            ('(3.14159,2.71828)', '(3.14159,2.71828)', True),
            # Mixed integer and float
            ('[0,1.5]', '[0,1.5]', True),
            ('(1.0,10)', '(1.0,10)', True),
            # Negative values
            ('[-10.5,10.5]', '[-10.5,10.5]', True),
            ('(-1.23,1.23)', '(-1.23,1.23)', True),
            # Single-sided with floats
            ('[3.14,)', '[3.14,)', True),
            ('(,-2.718]', '(,-2.718]', True),
            # Scientific notation should fail
            ('[1e-3,1e3]', '', False),
            ('(1E-5,1E5)', '', False),
            ('[2.5e10,3.0E-2]', '', False),
        ],
    )
    def test_string_representation(self, range_str, expected_str, should_pass):
        """Test string representation of bounds and verify scientific notation fails."""
        if should_pass:
            bound = Bound(range_str)
            assert str(bound) == expected_str
        else:
            with pytest.raises(ValueError, match='Invalid range format'):
                Bound(range_str)

    @pytest.mark.parametrize(
        'invalid_range,should_raise',
        [
            ('invalid', True),
            ('[0,1,2]', True),
        ],
    )
    def test_invalid_range_format(self, invalid_range, should_raise):
        """Test that invalid range formats raise errors."""
        if should_raise:
            with pytest.raises(ValueError, match='Invalid range format'):
                Bound(invalid_range)
        else:
            Bound(invalid_range)  # Should not raise


class TestBoundSlackModeClamp:
    """Slack tolerance, configurable failure mode, and clamping on `Bound`."""

    @pytest.mark.parametrize(
        'value,accepted',
        [
            (1.0, True),  # inside the core interval
            (2.0 + 5e-7, True),  # just above upper, within slack
            (-5e-7, True),  # just below lower, within slack
            (2.1, False),  # beyond the slack band
            (-0.1, False),  # beyond the slack band
        ],
    )
    def test_slack_widens_acceptance(self, value, accepted):
        bound = Bound('[0,2]', slack=1e-6)
        if accepted:
            assert bound.check(value) == value
        else:
            with pytest.raises(ValueError):
                bound.check(value)

    @pytest.mark.parametrize('value', [0.0, 1.0])
    def test_slack_zero_preserves_open_interval(self, value):
        """slack=0 keeps exact inclusivity: open bounds still reject the endpoints."""
        with pytest.raises(ValueError):
            Bound('(0,1)').check(value)

    def test_slack_message_notes_tolerance(self):
        with pytest.raises(ValueError, match=r'must be in \[0,2\] \(±0.001\)'):
            Bound('[0,2]', slack=1e-3).check(3.0)

    @pytest.mark.parametrize(
        'value,expected',
        [
            (2.0004, 2.0),  # upper slack region -> snapped to max
            (-0.0004, 0.0),  # lower slack region -> snapped to min
            (1.0, 1.0),  # core value untouched
        ],
    )
    def test_clamp_scalar(self, value, expected):
        bound = Bound('[0,2]', slack=1e-3, clamp=True)
        assert bound.check(value) == pytest.approx(expected)

    def test_clamp_array_snaps_out_of_core(self):
        bound = Bound('[0,2]', slack=1e-3, clamp=True)
        result = bound.check(np.array([-0.0005, 1.0, 2.0004]))
        assert np.allclose(result, [0.0, 1.0, 2.0])

    def test_log_mode_keeps_value_and_warns(self, monkeypatch):
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())
        bound = Bound('[0,2]', slack=1e-6, on_violation='log')
        # beyond the slack band: kept (not raised), warning emitted with disposition 'kept'
        assert bound.check(2.5) == 2.5
        _, kwargs = dt_module.LOGGER.warning.call_args
        assert kwargs['disposition'] == 'kept'

    @pytest.mark.parametrize(
        'value,expected',
        [
            (2.5, 2.0),  # beyond upper band -> coerced to max, not kept
            (-5.0, 0.0),  # beyond lower band -> coerced to min
        ],
    )
    def test_log_clamp_coerces_beyond_band(self, value, expected, monkeypatch):
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())
        bound = Bound('[0,2]', slack=1e-3, on_violation='log', clamp=True)
        assert bound.check(value) == pytest.approx(expected)
        _, kwargs = dt_module.LOGGER.warning.call_args
        assert kwargs['disposition'] == 'clamped'

    def test_log_mode_array_keeps_values(self, monkeypatch):
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())
        bound = Bound('[0,2]', on_violation='log')
        result = bound.check(np.array([1.0, 2.5, -1.0]))
        assert np.allclose(result, [1.0, 2.5, -1.0])
        dt_module.LOGGER.warning.assert_called_once()

    def test_log_mode_uses_section_context(self, monkeypatch):
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())
        section = Mock()
        section.m_def.name = 'MySection'
        section.m_path.return_value = '/data/outputs/0'
        Bound('[0,2]', on_violation='log').check(5.0, section=section)
        _, kwargs = dt_module.LOGGER.warning.call_args
        assert kwargs['section'] == 'MySection'
        assert kwargs['path'] == '/data/outputs/0'

    @pytest.mark.parametrize('kwargs', [{'on_violation': 'boom'}, {'slack': -1.0}])
    def test_invalid_configuration_rejected(self, kwargs):
        with pytest.raises(ValueError):
            Bound('[0,1]', **kwargs)

    def test_knobs_survive_serialization_roundtrip(self):
        original = m_float_bounded(
            dtype=float,
            bound=Bound('[0,2]', slack=1e-3, on_violation='log', clamp=True),
        )
        serialized = original.serialize_self()
        assert serialized['type_bound_slack'] == pytest.approx(1e-3)
        assert serialized['type_bound_on_violation'] == 'log'
        assert serialized['type_bound_clamp'] is True

        reconstructed = m_float_bounded()
        reconstructed.normalize_flags(serialized)
        assert reconstructed.bound.slack == pytest.approx(1e-3)
        assert reconstructed.bound.on_violation == 'log'
        assert reconstructed.bound.clamp is True

    def test_defaults_unchanged_when_unused(self):
        bound = Bound('[0,2]')
        assert bound.slack == 0.0
        assert bound.on_violation == 'raise'
        assert bound.clamp is False

    @pytest.mark.parametrize('spec', ['(0,1)', '(0,10]', '[0,1)'])
    def test_clamp_rejected_on_open_finite_bound(self, spec):
        # clamp would snap to an excluded endpoint; refuse at construction
        with pytest.raises(
            ValueError, match='clamp=True requires closed finite bounds'
        ):
            Bound(spec, clamp=True)

    @pytest.mark.parametrize('spec', ['[0,1]', '[0,)', '(,0]', ''])
    def test_clamp_allowed_on_closed_or_infinite_bounds(self, spec):
        Bound(spec, clamp=True)  # closed finite, or infinite sides -> fine

    def test_clamp_int_array_stays_in_range(self, monkeypatch):
        # a fractional bound must not truncate an int array back below the bound
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())
        bound = Bound('[2.5,10]', clamp=True, on_violation='log')
        result = bound.check(np.array([0, 5, 20], dtype=np.int64))
        assert np.all(result >= 2.5) and np.all(result <= 10)
        assert np.allclose(result, [2.5, 5.0, 10.0])

    def test_log_value_range_excludes_nan(self, monkeypatch):
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())
        # NaN passes the check, so it must not poison the reported offending range
        Bound('[0,2]', on_violation='log').check([np.nan, 5.0])
        _, kwargs = dt_module.LOGGER.warning.call_args
        assert kwargs['value_range'] == [5.0, 5.0]

    def test_int_bounded_slack_and_clamp(self):
        # the knobs work through m_int_bounded, not only the raw Bound
        datatype = setup_datatype_for_testing(
            m_int_bounded(dtype=int, bound=Bound('[0,10]', slack=2, clamp=True))
        )
        assert datatype.normalize(11) == 10  # within slack, clamped to max
        assert datatype.normalize(5) == 5

    def test_log_mode_end_to_end_through_section(self, monkeypatch):
        # drive on_violation='log' through a real Section assignment (section context)
        monkeypatch.setattr(dt_module, 'LOGGER', Mock())

        class S(Section):
            x = Quantity(
                type=m_float_bounded(
                    dtype=float, bound=Bound('[0,2]', on_violation='log')
                ),
                unit='joule',
            )

        section = S()
        section.x = 5.0 * ureg.joule  # out of bounds, but logged and kept, not raised
        assert section.x.magnitude == 5.0
        _, kwargs = dt_module.LOGGER.warning.call_args
        assert kwargs['disposition'] == 'kept'
        assert kwargs['section'] == 'S'


class TestScaleInvariance:
    """`is_scale_invariant` and the `flexible_unit` guard on first assignment."""

    @pytest.mark.parametrize(
        'kwargs,invariant',
        [
            ({}, True),  # unbounded
            ({'range_str': '[0,)'}, True),  # non-negative (positive_float)
            ({'range_str': '(0,)'}, True),  # strictly positive
            ({'range_str': '(,0]'}, True),  # non-positive
            ({'range_str': '[0,1]'}, False),  # nonzero upper endpoint
            ({'range_str': '[1,)'}, False),  # nonzero lower endpoint
            ({'range_str': '[0,)', 'slack': 1e-3}, False),  # slack is absolute
        ],
    )
    def test_is_scale_invariant(self, kwargs, invariant):
        range_str = kwargs.pop('range_str', '')
        assert Bound(range_str, **kwargs).is_scale_invariant() is invariant

    def test_flexible_unit_allows_scale_invariant_bound(self):
        # non-negativity holds under any positive unit rescale
        class Ok(Section):
            x = Quantity(
                type=m_float_bounded(dtype=float, bound=Bound('[0,)')),
                unit='joule',
                flexible_unit=True,
            )

        section = Ok()
        section.x = 5.0 * ureg.eV  # different unit, still >= 0
        assert section.x.magnitude > 0

    @pytest.mark.parametrize(
        'bounded_cls,dtype,bound',
        [
            (m_float_bounded, float, Bound('[0,1]')),  # nonzero finite endpoint
            (m_float_bounded, float, Bound('[0,)', slack=1e-3)),  # absolute slack
            (m_int_bounded, int, Bound('[1,10]')),  # int guard, nonzero endpoint
        ],
    )
    def test_flexible_unit_rejects_scale_dependent_bound(
        self, bounded_cls, dtype, bound
    ):
        # the guard lives in both bounded types' normalize; cover int and float
        class Bad(Section):
            x = Quantity(
                type=bounded_cls(dtype=dtype, bound=bound),
                unit='joule',
                flexible_unit=True,
            )

        with pytest.raises(ValueError, match='ill-defined on a flexible_unit'):
            Bad().x = 5 * ureg.joule

    def test_scale_dependent_bound_fine_without_flexible_unit(self):
        class Fine(Section):
            x = Quantity(
                type=m_float_bounded(dtype=float, bound=Bound('[0,1]')),
                unit='joule',
            )

        section = Fine()
        section.x = 0.5 * ureg.joule
        assert section.x.magnitude == 0.5


class TestBoundedTypes:
    """Test the m_int_bounded and m_float_bounded class functionality."""

    @pytest.mark.parametrize(
        'dtype,bounds_str,test_value,should_pass',
        [
            # Basic functionality
            (int, '[0,10]', 5, True),
            (int, '[0,10]', 0, True),
            (int, '[0,10]', 10, True),
            (int, '[0,10]', -1, False),
            (int, '[0,10]', 11, False),
            # Special values
            (float, '[0,1]', float('nan'), True),
            (float, '[0,1]', None, True),
            # Array validation
            (int, '[0,10]', [1, 5, 9], True),
            (int, '[0,10]', [1, 15, 9], False),
            (int, '[0,10]', [], True),
            # Various dtypes and bounds
            (m_int32(), '[1,10]', 5, True),
            (m_int32(), '[1,10]', 0, False),
            (m_float64(), '(0,1)', 0.5, True),
            (m_float64(), '(0,1)', 0.0, False),
            (m_int16(), '[0,)', 100, True),
            (m_int16(), '[0,)', -1, False),
            (m_float32(), '(,0]', -5.0, True),
            (m_float32(), '(,0]', 1.0, False),
        ],
    )
    def test_normalization(self, dtype, bounds_str, test_value, should_pass):
        """Test value normalization with various dtypes and bounds."""
        bound = Bound(bounds_str)
        shape = ['*'] if isinstance(test_value, list) else None

        # Extract the underlying dtype if it's a datatype instance
        if hasattr(dtype, '_dtype'):
            underlying_dtype = dtype._dtype
        else:
            underlying_dtype = dtype

        # Choose appropriate bounded type based on dtype
        dtype_name = (
            str(type(dtype).__name__) if not isinstance(dtype, type) else dtype.__name__
        )
        if underlying_dtype is int or 'int' in dtype_name.lower():
            bounded_type = m_int_bounded(dtype=underlying_dtype, bound=bound)
        else:
            bounded_type = m_float_bounded(dtype=underlying_dtype, bound=bound)

        datatype = setup_datatype_for_testing(bounded_type, shape=shape)

        if should_pass:
            result = datatype.normalize(test_value)
            if test_value is None:
                assert result is None
            elif isinstance(test_value, float) and np.isnan(test_value):
                assert np.isnan(result)
            elif isinstance(test_value, list):
                if len(test_value) == 0:
                    assert len(result) == 0
                else:
                    # Check array content
                    if isinstance(result, np.ndarray):
                        if any(np.isnan(v) for v in test_value if isinstance(v, float)):
                            # Handle NaN in arrays
                            for i, v in enumerate(test_value):
                                if isinstance(v, float) and np.isnan(v):
                                    assert np.isnan(result[i])
                                else:
                                    assert result[i] == v
                        else:
                            assert np.array_equal(result, test_value)
                    else:
                        assert result == test_value
            else:
                assert result == test_value
        else:
            with pytest.raises(ValueError):
                datatype.normalize(test_value)

    @pytest.mark.parametrize(
        'bounded_class,dtype,other_type,should_convert',
        [
            (m_int_bounded, int, np.int32, True),
            (m_int_bounded, int, float, False),
            (m_float_bounded, float, float, True),
            (m_float_bounded, float, np.int32, False),
            (m_int_bounded, np.int32, np.int16, True),
            (m_float_bounded, np.float64, np.float32, True),
        ],
    )
    def test_convertible_from(self, bounded_class, dtype, other_type, should_convert):
        """Test convertible_from for bounded types."""
        bound = Bound('[0,10]')
        datatype = bounded_class(dtype=dtype, bound=bound)
        assert datatype.convertible_from(other_type) is should_convert

    @pytest.mark.parametrize(
        'bounded_class,dtype,expected_type',
        [
            (m_int_bounded, int, 'int'),
            (m_float_bounded, float, 'float'),
        ],
    )
    def test_standard_type_delegation(self, bounded_class, dtype, expected_type):
        """Test that standard_type returns correct type."""
        datatype = bounded_class(dtype=dtype, bound=Bound('[0,1]'))
        assert datatype.standard_type() == expected_type

    def test_serialization_and_reconstruction(self):
        """A bounded type serializes as a custom datatype so `normalize_type` reloads the
        exact class and the bound survives, rather than collapsing to a plain base type
        that drops the interval."""
        original = m_float_bounded(dtype=float, bound=Bound('[0,1]'))
        serialized = original.serialize_self()

        assert serialized['type_kind'] == 'custom'
        assert (
            serialized['type_data']
            == 'nomad_simulations.schema_packages.data_types.m_float_bounded'
        )
        assert serialized['type_dtype'] == 'float'
        assert serialized['type_bound'] == '[0,1]'

        reconstructed = normalize_type(serialized)
        assert isinstance(reconstructed, m_float_bounded)
        assert reconstructed._dtype is float
        test_datatype = setup_datatype_for_testing(reconstructed, shape=None)

        # the reconstructed type still enforces the bound
        assert test_datatype.normalize(0.5) == 0.5
        with pytest.raises(ValueError):
            test_datatype.normalize(1.5)

    # Each case is a self-contained snapshot of a serialized shape the schema has emitted
    # for a plain `[0,1]` bound. `_deserialize_bounded_type` fills defaults for absent
    # keys, so every one must reconstruct to the same type with default knobs. Add a case
    # on every serialization bump (see `_deserialize_bounded_type`) to keep older shapes
    # readable.
    @pytest.mark.parametrize(
        'serialized',
        [
            pytest.param(
                {
                    'type_kind': 'custom',
                    'type_data': _M_FLOAT_BOUNDED_PATH,
                    'type_dtype': 'float',
                    'type_bound': '[0,1]',
                    'type_bound_slack': 0.0,
                    'type_bound_on_violation': 'raise',
                    'type_bound_clamp': False,
                },
                id='explicit-default-knobs',
            ),
            pytest.param(
                {
                    'type_kind': 'custom',
                    'type_data': _M_FLOAT_BOUNDED_PATH,
                    'type_dtype': 'float',
                    'type_bound': '[0,1]',
                },
                id='omitted-default-knobs',
            ),
        ],
    )
    def test_deserialize_tolerates_serialization_variants(self, serialized):
        """Every serialized variant of a plain `[0,1]` bound reconstructs to the same
        `m_float_bounded` with default knobs, since absent keys fall back to defaults."""
        reconstructed = normalize_type(dict(serialized))
        assert isinstance(reconstructed, m_float_bounded)
        assert reconstructed._dtype is float
        assert str(reconstructed.bound) == '[0,1]'
        assert reconstructed.bound.slack == 0.0
        assert reconstructed.bound.on_violation == 'raise'
        assert reconstructed.bound.clamp is False

    def test_basic_functionality(self):
        """Test basic functionality of bounded types."""
        int_bounded = m_int_bounded(dtype=int, bound=Bound('[0,10]'))
        float_bounded = m_float_bounded(dtype=float, bound=Bound('[0.0,1.0]'))

        # Test basic functionality
        assert int_bounded.standard_type() == 'int'
        assert float_bounded.standard_type() == 'float'

        # Test convertibility
        assert int_bounded.convertible_from(np.int32) is True
        assert float_bounded.convertible_from(np.float32) is True


class TestNOMADIntegration:
    """Test integration with NOMAD's type system."""

    def test_normalize_type_string_resolution(self):
        """Test that string type references work."""
        # This tests the full NOMAD integration
        serialized_data = {
            'type_kind': 'custom',
            'type_data': 'nomad_simulations.schema_packages.data_types.m_float_bounded',
            'type_bound': '[0,1]',
        }

        # This is what NOMAD does internally
        datatype = normalize_type(serialized_data)
        assert isinstance(datatype, m_float_bounded)

        # Test it works
        test_instance = setup_datatype_for_testing(datatype, shape=None)
        assert test_instance.normalize(0.5) == 0.5
        with pytest.raises(ValueError):
            test_instance.normalize(1.5)

    def test_schema_definition_roundtrip_preserves_bound(self):
        """Serialize a whole quantity *definition* to a dict (as a YAML schema does) and
        rebuild it. The custom serialization lets `normalize_type` reload the exact
        bounded class, so the reconstructed definition keeps its bound and enforces it --
        the case the plain `python` kind broke."""
        from nomad.metainfo import Package

        pkg = Package(name='bound_roundtrip_pkg')
        section = Section(name='BoundRoundtripSec')
        pkg.m_add_sub_section(Package.section_definitions, section)
        section.m_add_sub_section(
            Section.quantities,
            Quantity(
                name='occ',
                type=m_float_bounded(dtype=float, bound=Bound('[0,2]', slack=1e-3)),
                shape=[],
            ),
        )
        pkg.init_metainfo()

        as_dict = pkg.m_to_dict(with_meta=True)
        serialized_type = as_dict['section_definitions'][0]['quantities'][0]['type']
        assert serialized_type['type_kind'] == 'custom'
        assert serialized_type['type_bound'] == '[0,2]'

        # rebuild the definition under a fresh name to avoid the metainfo registry clash
        as_dict['name'] = 'bound_roundtrip_pkg_rebuilt'
        rebuilt = Package.m_from_dict(as_dict)
        rebuilt.init_metainfo()
        rebuilt_type = rebuilt.section_definitions[0].quantities[0].type
        assert isinstance(rebuilt_type, m_float_bounded)
        assert rebuilt_type.bound.slack == pytest.approx(1e-3)

        instance = rebuilt.section_definitions[0].section_cls()
        instance.occ = 1.5  # within [0,2]
        assert instance.occ == 1.5
        with pytest.raises(ValueError):
            instance.occ = 3.0  # beyond [0,2] + slack

    @pytest.mark.parametrize(
        'section_data,should_pass',
        [
            (
                {'bounded_value': 0.75, 'bounded_array': [1, 5, 8, 10]},
                True,
            ),
            (
                {'bounded_value': 1.5, 'bounded_array': [1, 15, 8]},
                False,
            ),
        ],
    )
    def test_section_serialization_deserialization(self, section_data, should_pass):
        """Test full section serialization/deserialization cycle with BoundedNumber."""
        if should_pass:
            # Test successful round-trip
            original_section = TestSection()
            original_section.bounded_value = section_data['bounded_value']
            original_section.bounded_array = section_data['bounded_array']

            # Serialize to dict
            serialized_dict = original_section.m_to_dict()

            # Verify the serialized data contains our values
            assert serialized_dict['bounded_value'] == section_data['bounded_value']
            assert serialized_dict['bounded_array'] == section_data['bounded_array']

            # Deserialize back to a new section
            reconstructed_section = TestSection.m_from_dict(serialized_dict)

            # Verify the reconstructed section has correct values
            assert reconstructed_section.bounded_value == section_data['bounded_value']
            assert reconstructed_section.bounded_array == section_data['bounded_array']

            # Verify bounds checking still works on reconstructed section
            with pytest.raises(ValueError):
                reconstructed_section.bounded_value = 1.5  # Out of bounds

            with pytest.raises(ValueError):
                reconstructed_section.bounded_array = [1, 15, 8]  # 15 out of bounds

            # Verify valid values still work
            reconstructed_section.bounded_value = 0.25
            reconstructed_section.bounded_array = [2, 3, 4]
            assert reconstructed_section.bounded_value == 0.25
            assert reconstructed_section.bounded_array == [2, 3, 4]
        else:
            # Test that invalid data fails during deserialization
            with pytest.raises(ValueError):
                TestSection.m_from_dict(section_data)

    @pytest.mark.parametrize(
        'compatibility_type,dtype,bounds_str,expected',
        [
            ('elasticsearch', float, '[0,1]', 'double'),
            ('elasticsearch', int, '[0,100]', 'long'),
            ('mongodb_float', float, '[0,1]', 'FloatField'),
            ('mongodb_int', int, '[0,100]', 'IntField'),
            ('json_schema_float', float, '[0,1]', {'type': 'number'}),
            ('json_schema_int', int, '[0,100]', {'type': 'integer'}),
        ],
    )
    def test_external_system_compatibility(
        self, compatibility_type, dtype, bounds_str, expected
    ):
        """Test that bounded types map correctly for external systems."""
        # Extract the underlying dtype if it's a datatype instance
        if hasattr(dtype, '_dtype'):
            underlying_dtype = dtype._dtype
        else:
            underlying_dtype = dtype

        if underlying_dtype is int:
            bounded_type = m_int_bounded(
                dtype=underlying_dtype, bound=Bound(bounds_str)
            )
        else:
            bounded_type = m_float_bounded(
                dtype=underlying_dtype, bound=Bound(bounds_str)
            )

        if compatibility_type == 'elasticsearch':
            try:
                from nomad.metainfo.data_type import to_elastic_type

                assert to_elastic_type(bounded_type, dynamic=True) == expected
            except ImportError:
                pytest.skip('to_elastic_type not available')
        elif compatibility_type.startswith('mongodb'):
            try:
                from mongoengine import FloatField, IntField
                from nomad.metainfo.data_type import to_mongo_type

                expected_class = FloatField if expected == 'FloatField' else IntField
                assert to_mongo_type(bounded_type) == expected_class
            except ImportError:
                pytest.skip('mongoengine or to_mongo_type not available')
        elif compatibility_type.startswith('json_schema'):
            try:
                from nomad.metainfo.data_type import to_json_schema_type

                assert to_json_schema_type(bounded_type) == expected
            except ImportError:
                pytest.skip('to_json_schema_type not available')


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.parametrize(
        'bounds_str,test_values,should_pass,error_match',
        [
            # Mixed valid/invalid values
            ('[0,10]', [1, 5, 15, 8], False, r'All values must be in \[0,10\]'),
            # Empty arrays
            ('[0,10]', [], True, None),
            # Infinity bounds
            ('[0,)', [1e10], True, None),
            ('[0,)', [-1], False, None),
            ('(,0]', [-1e10], True, None),
            ('(,0]', [1], False, None),
        ],
    )
    def test_edge_case_arrays(self, bounds_str, test_values, should_pass, error_match):
        """Test edge cases with array values."""
        bound = Bound(bounds_str)
        dtype = float if any(isinstance(v, float) for v in test_values) else int
        if dtype is int:
            bounded_type = m_int_bounded(dtype=dtype, bound=bound)
        else:
            bounded_type = m_float_bounded(dtype=dtype, bound=bound)
        datatype = setup_datatype_for_testing(bounded_type, shape=['*'])

        if should_pass:
            result = datatype.normalize(test_values)
            if len(test_values) == 0:
                assert len(result) == 0
            else:
                # For large numbers, just check they're processed
                assert len(result) == len(test_values)
        else:
            if error_match:
                with pytest.raises(ValueError, match=error_match):
                    datatype.normalize(test_values)
            else:
                with pytest.raises(ValueError):
                    datatype.normalize(test_values)

    @pytest.mark.parametrize(
        'bounds_str,valid_val,invalid_val',
        [
            ('[0,1]', 0.5, 1.5),  # closed interval
            ('(0,1)', 0.5, 0.0),  # open interval
            ('[0,)', 100, -1),  # half-bounded
            ('', 0, None),  # unbounded (no invalid values)
        ],
    )
    def test_reconstruct_with_complex_bounds(self, bounds_str, valid_val, invalid_val):
        """The bound survives reconstruction, so the reconstructed type accepts valid
        values and still rejects out-of-bound ones."""
        original = m_float_bounded(dtype=float, bound=Bound(bounds_str))
        serialized = original.serialize_self()
        reconstructed = normalize_type(serialized)

        test_instance = setup_datatype_for_testing(reconstructed, shape=None)

        # Valid value should work
        assert test_instance.normalize(valid_val) == valid_val

        # The reconstructed bound still enforces the interval
        if invalid_val is not None:
            with pytest.raises(ValueError):
                test_instance.normalize(invalid_val)


class TestUnitHandling:
    """Test unit preservation and handling with BoundedNumber."""

    @pytest.mark.parametrize('dtype', [float, int, m_float64(), m_int32()])
    @pytest.mark.parametrize('bounds_str', ['[0,10]', '(0,1)', '[0,)'])
    @pytest.mark.parametrize('unit_str', ['joule', 'meter', 'second'])
    def test_unit_preservation_scalar(self, dtype, bounds_str, unit_str):
        """Test that units are preserved for scalar values."""

        # Extract the underlying dtype if it's a datatype instance
        if hasattr(dtype, '_dtype'):
            underlying_dtype = dtype._dtype
        else:
            underlying_dtype = dtype

        dtype_name = (
            str(type(dtype).__name__) if not isinstance(dtype, type) else dtype.__name__
        )
        if underlying_dtype is int or 'int' in dtype_name.lower():

            class TestUnitSection(Section):
                bounded_quantity = Quantity(
                    type=m_int_bounded(dtype=underlying_dtype, bound=Bound(bounds_str)),
                    unit=unit_str,
                )
        else:

            class TestUnitSection(Section):
                bounded_quantity = Quantity(
                    type=m_float_bounded(
                        dtype=underlying_dtype, bound=Bound(bounds_str)
                    ),
                    unit=unit_str,
                )

        section = TestUnitSection()

        # Test with valid value within bounds, compatible with dtype
        if bounds_str == '[0,10]':
            test_value = 5.0
        elif bounds_str == '(0,1)':
            if 'int' in str(dtype).lower() or (
                isinstance(dtype, type) and dtype is int
            ):
                pytest.skip('Cannot convert 0.5 to integer type')
            test_value = 0.5
        elif bounds_str == '[0,)':
            test_value = 100.0

        # Assign value with unit
        section.bounded_quantity = test_value * getattr(ureg, unit_str)

        # Check that value is a Pint quantity with correct unit
        assert hasattr(section.bounded_quantity, 'magnitude')
        assert hasattr(section.bounded_quantity, 'units')
        assert section.bounded_quantity.magnitude == test_value
        assert str(section.bounded_quantity.units) == unit_str

    @pytest.mark.parametrize('dtype', [float, int])
    @pytest.mark.parametrize('unit_str', ['joule', 'meter'])
    def test_unit_preservation_array(self, dtype, unit_str):
        """Test that units are preserved for array values."""

        if dtype is int:

            class TestUnitSection(Section):
                bounded_array = Quantity(
                    type=m_int_bounded(dtype=dtype, bound=Bound('[0,10]')),
                    shape=['*'],
                    unit=unit_str,
                )
        else:

            class TestUnitSection(Section):
                bounded_array = Quantity(
                    type=m_float_bounded(dtype=dtype, bound=Bound('[0,10]')),
                    shape=['*'],
                    unit=unit_str,
                )

        section = TestUnitSection()
        test_values = [1.0, 5.0, 9.0]

        # Assign array with unit
        section.bounded_array = test_values * getattr(ureg, unit_str)

        # Check that value is a Pint quantity with correct unit
        assert hasattr(section.bounded_array, 'magnitude')
        assert hasattr(section.bounded_array, 'units')
        assert np.allclose(section.bounded_array.magnitude, test_values)
        assert str(section.bounded_array.units) == unit_str

    @pytest.mark.parametrize('dtype', [float, int])
    @pytest.mark.parametrize(
        'unit_conversion,source_value,bounds_str',
        [
            (('kilojoule', 'joule', 1000.0), 0.005, '[0,10]'),  # 0.005 kJ = 5 J
            (('centimeter', 'meter', 0.01), 500.0, '[0,1000]'),  # 500 cm = 5 m
            (('millisecond', 'second', 0.001), 5000.0, '[0,10000]'),  # 5000 ms = 5 s
        ],
    )
    def test_unit_conversion(self, dtype, unit_conversion, source_value, bounds_str):
        """Test that unit conversion works correctly with bounds checking."""
        from_unit, to_unit, conversion_factor = unit_conversion

        # Skip int tests for non-integer source values
        if dtype is int and not source_value.is_integer():
            pytest.skip('Cannot convert non-integer to int type')

        class TestUnitSection(Section):
            if dtype is int:
                bounded_quantity = Quantity(
                    type=m_int_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit=to_unit,  # Target unit
                )
            else:
                bounded_quantity = Quantity(
                    type=m_float_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit=to_unit,  # Target unit
                )

        section = TestUnitSection()

        # Assign value in source unit (should be converted to target unit)
        section.bounded_quantity = source_value * getattr(ureg, from_unit)

        # Check that value was converted and bounds still work
        assert hasattr(section.bounded_quantity, 'magnitude')
        expected_magnitude = source_value * conversion_factor
        assert np.isclose(section.bounded_quantity.magnitude, expected_magnitude)
        assert str(section.bounded_quantity.units) == to_unit

    @pytest.mark.parametrize('dtype', [float, int])
    @pytest.mark.parametrize(
        'bounds_str,valid_value,invalid_value',
        [('[0,10]', 5.0, 15.0), ('(0,1)', 0.5, 1.5), ('[0,)', 100.0, -1.0)],
    )
    def test_bounds_checking_with_units(
        self, dtype, bounds_str, valid_value, invalid_value
    ):
        """Test that bounds checking works correctly with unit quantities."""

        # Skip integer types for (0,1) bounds since 0.5 can't convert to int
        if dtype is int and bounds_str == '(0,1)':
            pytest.skip('Cannot convert 0.5 to integer type')

        class TestUnitSection(Section):
            if dtype is int:
                bounded_quantity = Quantity(
                    type=m_int_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit='joule',
                )
            else:
                bounded_quantity = Quantity(
                    type=m_float_bounded(dtype=dtype, bound=Bound(bounds_str)),
                    unit='joule',
                )

        section = TestUnitSection()

        # Valid value should work
        section.bounded_quantity = valid_value * ureg.joule
        assert section.bounded_quantity.magnitude == valid_value

        # Invalid value should fail
        with pytest.raises(ValueError, match=r'All values must be in'):
            section.bounded_quantity = invalid_value * ureg.joule

    def test_unit_stripping_during_normalization(self):
        """Test that units are properly handled during the normalization process."""
        bounded_type = m_float_bounded(dtype=float, bound=Bound('[0,10]'))
        bounded_type = setup_datatype_for_testing(bounded_type, shape=None)
        quantity_value = 5.0 * ureg.joule

        # Direct normalization should extract magnitude
        normalized = bounded_type.normalize(quantity_value)
        assert normalized == 5.0
        assert not hasattr(normalized, 'magnitude')  # Plain float

        # in a Quantity with unit, NOMAD should wrap it back
        class TestUnitSection(Section):
            test_quantity = Quantity(
                type=m_float_bounded(dtype=float, bound=Bound('[0,10]')), unit='joule'
            )

        section = TestUnitSection()
        section.test_quantity = quantity_value

        # Should be wrapped back as a quantity
        assert hasattr(section.test_quantity, 'magnitude')
        assert section.test_quantity.magnitude == 5.0

    def test_serialization_with_units(self):
        """Test that serialization works correctly with unit quantities."""

        # Create and populate section using module-level class
        original_section = TestUnitSerializationSection()
        test_value = 5.0
        original_section.bounded_quantity = test_value * ureg.joule

        # Serialize and deserialize
        serialized = original_section.m_to_dict()
        reconstructed_section = TestUnitSerializationSection.m_from_dict(serialized)

        # Check that units and bounds are preserved
        assert hasattr(reconstructed_section.bounded_quantity, 'magnitude')
        assert reconstructed_section.bounded_quantity.magnitude == test_value
        assert str(reconstructed_section.bounded_quantity.units) == 'joule'

        # Check that bounds checking still works
        invalid_value = 15.0
        with pytest.raises(ValueError):
            reconstructed_section.bounded_quantity = invalid_value * ureg.joule
