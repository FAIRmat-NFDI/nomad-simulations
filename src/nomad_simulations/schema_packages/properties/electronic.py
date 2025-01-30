from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection, MEnum
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad_simulations.schema_packages.general import ModelBaseSection
import plotly.graph_objects as go

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)

m_package = SchemaPackage()


SingleElectronSimpleSpin = Quantity(
    type=MEnum('alpha', 'beta'),
    default='alpha',
    description='Simple spin',
)

HighestOccupiedEnergy = Quantity(
    type=np.float64,
    unit='J',
    description='Highest occupied energy level.',
)

LowestUnoccupiedEnergy = Quantity(
    type=np.float64,
    unit='J',
    description='Lowest unoccupied energy level.',
)

BandGap = Quantity(
    type=np.float64,
    unit='J',
    description='''
    The gap between the highest occupied state and the lowest unoccupied state.
    `None` shows that the band gap was not extracted.
    ''',
)


class m_unit64(m_float64):
    pass


class ElectronicEigenvalues(ModelBaseSection):
    """Eigenvalues of the electronic states"""

    spin = SingleElectronSimpleSpin

    semantic_group = placeholder

    energies = Quantity(
        type=np.float64,
        unit='J',
        shape=['*'],
        description='The eigenstate obtained from solving the electronic Schrödinger equation',  # ! re-word
    )

    occupations = Quantity(
        type=m_unit64,
        shape=['*'],
        description='Occupation of the states',
    )

    highest_occupied_energy = HighestOccupiedEnergy

    lowest_unoccupied_energy = LowestUnoccupiedEnergy

    energy_gap = BandGap

    def name_from_section(self) -> str:
        try:
            return f"{self.semantic_group.name_from_section()} {self.spin}"
        except AttributeError:
            return self.spin


class DensityOfStates(ModelBaseSection):
    spin = SingleElectronSimpleSpin

    semantic_group = placeholder

    energies = Quantity(
        type=np.float64,
        unit='J',
        shape=['*'],
        description='The eigenstate obtained from solving the electronic Schrödinger equation',  # ! re-word
    )

    values = Quantity(
        type=np.float64,
        # ? unit='1/J',
        shape=['*'],
        description='Density of states',
    )

    def name_from_section(self) -> str:
        pass

    def plot(self) -> go.Scatter:
        return go.Scatter(
            x=self.energies,
            y=self.values,
            mode='lines',
            name=self.name_from_section(),
        )


class KPoint(ModelBaseSection):
    """K-point in reciprocal space"""

    k_point = Quantity(
        type=np.float64,
        shape=["*"],
        unit='1/m',
        description='The k-point in reciprocal space',
    )

    high_symmetry_label = Quantity(
        type=str,  # ! MEnum
        description='High symmetry label of the k-point',
    )

    def name_from_section(self) -> str:
        return self.high_symmetry_label
        

class KResolvedElectronicEigenvalues(ElectronicEigenvalues):
    k_point = SubSection(sub_section=KPoint.m_def)


class KResolvedElectronicProperties(PlotSection, ModelBaseSection):
    """Collection section specialized in grouping together electronic properties defined by the k-space,
    e.g. electronic eigenvalues, band structure, density of states, etc.
    Due to the inconsistent nature of the Fermi level, we use `highest_occupied_state`, extracted from `eigenvalues`."""

    m_def = Section()

    k_path = SubSection(sub_section=KPoint.m_def, repeats=True)

    eigenvalues = SubSection(sub_section=KResolvedElectronicEigenvalues.m_def, repeats=True)

    dos = SubSection(sub_section=DensityOfStates.m_def, repeats=True)

    highest_occupied_energy = HighestOccupiedEnergy.m_def.m_copy()
    highest_occupied_energy.description += "Here it spans the whole sampled K-space."

    lowest_unoccupied_energy = LowestUnoccupiedEnergy.m_def.m_copy()
    lowest_unoccupied_energy.description += "Here it spans the whole sampled K-space."

    band_gap = BandGap.m_def.m_copy()
    band_gap.description += "At the level of a bulk material, this coincides with the band gap."
    
    def plot_dos(self) -> go.Figure:
        semantic_order = ('s', 'p', 'd', 'f')
        self.dos.sort(key=lambda dos: (semantic_order.index(dos.semantic_group), dos.spin))
        return go.Figure(data=[self.dos.plot() for dos in self.dos])
    
    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        # this does not check if the plot was already stored
        self.figures.append(
            PlotlyFigure(
                label='Full DOS',
                index=len(self.figures),
                figure=self.plot_dos().to_plotly_json(),
            )
        )


m_package.__init_metainfo__()
