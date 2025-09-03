from collections.abc import Callable

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.metainfo import Quantity
from plotly.graph_objects import Figure

from nomad_simulations.schema_packages.physical_property import PhysicalProperty

from . import logger


class DummyPhysicalProperty(PhysicalProperty):
    value = Quantity(
        type=np.float64,
        unit='eV',
        shape=['*', '*', '*', '*'],
        description="""
        This value is defined in order to test the functionality in `PhysicalProperty`.
        """,
    )

    def plot(self, **kwargs) -> list[PlotlyFigure]:
        """Test implementation of plot method."""
        fig = Figure()
        fig.add_scatter(x=[1, 2, 3], y=[1, 4, 2], name='test')
        plotly_figure = PlotlyFigure(label='test', figure=fig.to_plotly_json())
        return [plotly_figure]


class TestPhysicalProperty:
    """
    Test the `PhysicalProperty` class defined in `physical_property.py`.
    """

    def test_is_derived(self):
        """
        Test the `normalize` and `_is_derived` methods.
        """
        # Testing a directly parsed physical property
        not_derived_physical_property = PhysicalProperty()
        assert not_derived_physical_property._is_derived() is False
        not_derived_physical_property.normalize(EntryArchive(), logger)
        assert not_derived_physical_property.is_derived is False
        # Testing a derived physical property
        derived_physical_property = PhysicalProperty(
            physical_property_ref=not_derived_physical_property,
        )
        assert derived_physical_property._is_derived() is True
        derived_physical_property.normalize(EntryArchive(), logger)
        assert derived_physical_property.is_derived is True

    def test_normalization_flag(self):
        """
        Test that the normalization flag prevents duplicate normalization.
        """
        property_obj = DummyPhysicalProperty()

        # First normalization
        property_obj.normalize(EntryArchive(), logger)
        assert property_obj.m_cache.get('_is_normalized', False) is True

        # Store original figures count
        original_figures_count = len(property_obj.figures)

        # Second normalization should not duplicate work
        property_obj.normalize(EntryArchive(), logger)

        # Should still be marked as normalized
        assert property_obj.m_cache.get('_is_normalized', False) is True
        # Should not have duplicated figures
        assert len(property_obj.figures) == original_figures_count

    def test_plotting_and_contributions(self):
        """
        Test plotting integration and contributions normalization.
        """
        # Test main property plotting
        property_obj = DummyPhysicalProperty()
        property_obj.normalize(EntryArchive(), logger)

        assert len(property_obj.figures) > 0
        assert isinstance(property_obj.figures[0], PlotlyFigure)

        # Test contributions
        main_property = DummyPhysicalProperty()
        contribution = DummyPhysicalProperty(name='contribution')
        main_property.contributions = [contribution]
        main_property.normalize(EntryArchive(), logger)

        # Both should be normalized
        assert main_property.m_cache.get('_is_normalized', False) is True
        assert contribution.m_cache.get('_is_normalized', False) is True

    @pytest.mark.parametrize(
        'instantiator, reference',
        [
            (PhysicalProperty, 'PhysicalProperty'),
            (DummyPhysicalProperty, 'DummyPhysicalProperty'),
        ],
    )
    def test_name_setting_during_normalization(
        self, instantiator: Callable, reference: str
    ):
        """
        Test that the name is set during normalization for PhysicalProperty.
        """
        property_obj = instantiator()
        property_obj.normalize(EntryArchive(), logger)
        assert property_obj.name == reference

    @pytest.mark.parametrize(
        'has_nested_contributions, log_ref',
        [(True, True), (False, False)],
    )
    def test_contributions_validation(
        self, caplog, has_nested_contributions: bool, log_ref: bool
    ):
        """
        Test contributions validation during normalization.

        Args:
            has_nested_contributions: Whether to create nested contribution structure
            log_ref: Whether validation error should be logged
        """
        main_property = DummyPhysicalProperty(name='main')

        if has_nested_contributions:
            nested_contribution = DummyPhysicalProperty(name='nested')
            contribution_with_nested = DummyPhysicalProperty(name='parent_contribution')
            contribution_with_nested.contributions = [nested_contribution]
            main_property.contributions = [contribution_with_nested]
        else:
            contribution1 = DummyPhysicalProperty(name='contrib1')
            contribution2 = DummyPhysicalProperty(name='contrib2')
            main_property.contributions = [contribution1, contribution2]

        with caplog.at_level('ERROR'):
            main_property.normalize(EntryArchive(), logger)

        has_nested_error = any(
            'nested contributions' in record.message.lower()
            for record in caplog.records
        )
        assert has_nested_error == log_ref

        if log_ref:
            assert any('Contribution 0' in record.message for record in caplog.records)

    @pytest.mark.parametrize(
        'set_contribution_type_on_main, set_contribution_type_on_contrib, log_ref',
        [
            (False, False, False),
            (False, True, False),
            (True, False, True),
            (True, True, True),
        ],
    )
    def test_contribution_type_validation(
        self,
        caplog,
        set_contribution_type_on_main: bool,
        set_contribution_type_on_contrib: bool,
        log_ref: bool,
    ):
        """
        Test contribution_type validation during normalization.

        Args:
            set_contribution_type_on_main: Whether to set contribution_type on main property
            set_contribution_type_on_contrib: Whether to set contribution_type on contribution
            log_ref: Whether validation error should be logged
        """
        main_property = DummyPhysicalProperty(name='main')
        if set_contribution_type_on_main:
            main_property.contribution_type = 'invalid_main_type'

        contribution = DummyPhysicalProperty(name='contrib')
        if set_contribution_type_on_contrib:
            contribution.contribution_type = 'valid_contrib_type'

        main_property.contributions = [contribution]

        with caplog.at_level('ERROR'):
            main_property.normalize(EntryArchive(), logger)

        has_contrib_type_error = any(
            'contribution_type set but is not a contribution' in record.message.lower()
            for record in caplog.records
        )
        assert has_contrib_type_error == log_ref

    def test_is_contribution_method(self):
        """
        Test the _is_contribution helper method.
        """
        main_property = DummyPhysicalProperty(name='main')
        contribution = DummyPhysicalProperty(name='contrib')

        assert not main_property._is_contribution()
        assert not contribution._is_contribution()

        main_property.contributions = [contribution]
        main_property.normalize(EntryArchive(), logger)

        assert not main_property._is_contribution()
