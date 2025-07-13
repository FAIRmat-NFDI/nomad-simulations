import numpy as np
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

    def test_normalization_flag(self):
        """
        Test that the normalization flag prevents duplicate normalization.
        """
        property_obj = DummyPhysicalProperty(source='simulation')

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
        property_obj = DummyPhysicalProperty(source='simulation')
        property_obj.normalize(EntryArchive(), logger)

        assert len(property_obj.figures) > 0
        assert isinstance(property_obj.figures[0], PlotlyFigure)

        # Test contributions
        main_property = DummyPhysicalProperty(source='simulation')
        contribution = DummyPhysicalProperty(source='analysis', name='contribution')
        main_property.contributions = [contribution]
        main_property.normalize(EntryArchive(), logger)

        # Both should be normalized
        assert main_property.m_cache.get('_is_normalized', False) is True
        assert contribution.m_cache.get('_is_normalized', False) is True
