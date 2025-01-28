from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad_simulations.schema_packages.general import ModelBaseSection
import plotly.graph_objects as go
import plotly.express as px

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)

m_package = SchemaPackage()


class Spin(ModelBaseSection):
    pass


class DOS(PlotSection, ModelBaseSection):
    """Collection of Electronic Density of States"""

    m_def = Section()

    class SemanticDOS(ModelBaseSection):
        """Electronic Density of State set that has a clear semantic meaning,
        e.g. total DOS, projected DOS, etc."""

        class SpinResolvedDOS(ModelBaseSection):
            """Spin resolved DOS"""

            spin = Quantity(
                type=Spin,
                description='Spin channel',
            )

            values = Quantity(
                type=np.float64,
                shape=['*'],
                description='Actual DOS values',
            )  # ? add renormalized_values

            def name_from_section(self, section) -> str:
                return self.spin.name_from_section()

        label = Quantity(
            type=str,
            default='total',
            description='Label of the DOS',
        )  # TODO: el n m

        energies = Quantity(
            type=np.float64,
            unit='J',
            shape=['*'],
            description='Energy values at which the DOS is evaluated',
        )

        spin_channels = SubSection(subsection=SpinResolvedDOS.m_def, repeats=True)

        def name_from_section(self, section) -> str:
            if section.label:
                return section.label
            else:
                return 'total'

    collections = SubSection(subsection=SemanticDOS.m_def, repeats=True)

    def generate_plot(self) -> go.Figure:
        fig = go.Figure()
        for collection in self.collections:
            for spin_channel in collection.spin_channels:
                fig.add_trace(
                    px.line(
                        x=collection.energies,
                        y=spin_channel.values,
                        name=f'{collection.name_from_section()} {spin_channel.spin.name_from_section()}',
                    )
                )
        return fig
    
    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        # this does not check if the plot was already stored
        self.figures.append(
            PlotlyFigure(
                label='Full DOS',
                index=0,
                figure=self.generate_plot().to_plotly_json(),
            )
        )


m_package.__init_metainfo__()
