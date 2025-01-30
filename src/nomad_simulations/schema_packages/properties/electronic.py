from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection, MEnum
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad_simulations.schema_packages.general import ModelBaseSection
import plotly.graph_objects as go
import plotly.express as px

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)

m_package = SchemaPackage()


SingleElectronSimpleSpin = Quantity(
    type=MEnum('alpha', 'beta'),
    default='alpha',
    description='Simple spin',
)


class SpinResolvedDOS(ModelBaseSection):
    """Spin resolved DOS"""

    spin = SingleElectronSimpleSpin

    values = Quantity(
        type=np.float64,
        # unit='1/J',
        shape=['*'],
        description='Actual DOS values',
    )  # ? add renormalized_values

    def name_from_section(self) -> str:
        return self.spin
    

class SemanticDOS(ModelBaseSection):
    """Electronic Density of State set that has a clear semantic meaning,
    e.g. total DOS, projected DOS, etc."""

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

    spin_channels = SubSection(sub_section=SpinResolvedDOS.m_def, repeats=True)

    def name_from_section(self) -> str:
        if self.label:
            return self.label
        else:
            return 'total'


class DOS(PlotSection, ModelBaseSection):
    """Collection of Electronic Density of States"""

    m_def = Section()

    name = 'DOS'

    highest_occupied_state = Quantity(
        type=np.float64,
        unit='J',
        description="""
        Energy level denoting the origin along the energy axis, used for comparison and visualization. It is
        defined as the `ElectronicEigenvalues.highest_occupied_energy`.
        """,
    )

    collections = SubSection(sub_section=SemanticDOS.m_def, repeats=True)

    def generate_plot(self) -> go.Figure:
        fig = go.Figure()
        for collection in self.collections:
            for spin_channel in collection.spin_channels:
                fig.add_trace(
                    go.Scatter(
                        x=collection.energies,
                        y=spin_channel.values,
                        mode='lines',
                        name=f'{collection.name_from_section()} {spin_channel.name_from_section()}',
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
