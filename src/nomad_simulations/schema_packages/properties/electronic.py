from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config
from nomad.metainfo import placeholder, Quantity, SchemaPackage, Section, SubSection, MEnum, m_float64
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad_simulations.schema_packages.general import ModelBaseSection
from nomad_simulations.schema_packages.properties import energy
from nomad_simulations.schema_packages.atoms_state import Orbital
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

class ProjectionTarget(Orbital):
    element = Quantity(
        type=str,
    )

    atom_index = Quantity(
        type=int,
        shape=['*'],
    )

    def name_from_section(self) -> str:
        projected = False
        name = ''
        if self.element is not None:
            name += self.element
            projected = True
        if self.atom_index is not None:
            name += f'_{self.atom_index}'
            projected = True
        if self.l_quantum_symbols is not None:
            projected = True
            if self.n_quantum_numbers is not None:
                name += f' {self.n_quantum_numbers}{self.l_quantum_symbols}'
            else:
                name += f' {self.l_quantum_symbols}'
        return name if projected else 'total'


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


class m_unit64(m_float64):
    pass


class SemanticGroup(ModelBaseSection):
    """Group of electronic states with the same symmetry"""

    label = placeholder

    def name_from_section(self) -> str:  # !
        return self.semantic_group
    
    def plot(self) -> go.Scatter:
        """Generate an individual plotly plot."""

class SemanticGroupContainer(ModelBaseSection):
    """Container for semantic groups of electronic states""" # ! re-word

    m_def = Section()

    groups = SubSection(sub_section=SemanticGroup.m_def, repeats=True)

    def plot(self) -> go.Figure:
        figure = go.Figure()
        for group in self.groups:
            figure.add_trace(group.plot())
        return figure

class Frontiers(ModelBaseSection):
    """Frontiers of the electronic states"""

    highest_occupied_energy = energy.m_def.m_copy()

    lowest_unoccupied_energy = energy.m_def.m_copy()

    energy_gap = energy.m_def.m_copy()


class FermiRegion(ModelBaseSection):
    """Region around the Fermi level"""

    valence_band_maximum = energy.m_def.m_copy()

    condunction_band_minimum = energy.m_def.m_copy()
    # ? satellites

    fermi_level = energy.m_def.m_copy()
    # ! add 

    band_gap = energy.m_def.m_copy()
    # ! None

    parsed_quantities = Quantity(
        type=MEnum('valence band maximum', 'condunction band minimum', 'fermi level'),
        shape=['*'],
    )

    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        # mark which quantities were parsed
        for quantity in ('valence_band_maximum', 'condunction_band_minimum', 'fermi_level'):
            if getattr(self, quantity) is not None:
                self.parsed_quantities.append(quantity)  # ! initialize
        # compute band gap if not provided
        if self.band_gaps is None:
            try:
                self.band_gap = self.condunction_band_minimum - self.valence_band_maximum
            except (TypeError, AttributeError):
                pass


class ElectronicEigenvalues(SemanticGroupContainer):
    """Eigenvalues of the electronic states"""

    class EigenvalueGroup(SemanticGroup):

        class EigenvalueLabel(ProjectionTarget):  # ? necessary

            spin = SingleElectronSimpleSpin

            def name_from_section(self) -> str:
                try:
                    return f"{self.semantic_group.name_from_section()} {self.spin}"
                except AttributeError:
                    return self.spin

        label = SubSection(subsection=EigenvalueLabel.m_def)

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


class KResolvedElectronicEigenvalues(ElectronicEigenvalues):
    k_point = SubSection(sub_section=KPoint.m_def)


class DensityOfStates(SemanticGroupContainer):

    energies = Quantity(
        type=np.float64,
        unit='J',
        shape=['*'],
        description='The eigenstate obtained from solving the electronic Schrödinger equation',  # ! re-word
    )

    class DOSGroup(SemanticGroup):

        class DOSLabel(ProjectionTarget):
            spin = SingleElectronSimpleSpin
        
        label = SubSection(subsection=DOSLabel.m_def)

        values = Quantity(
            type=np.float64,
            # ? unit='1/J',
            shape=['*'],
            description='Density of states',
        )

        def plot(self) -> go.Scatter:
            return go.Scatter(
                x=self.m_parent.energies,  # ! check
                y=self.values,
                mode='lines',
                name=self.name_from_section(),
                legend_group=self.label.plotly_legend_group(),
                legendgrouptitle_text=self.label.plotly_legend_group(),
                visible=False,
            )

    groups = SubSection(sub_section=DOSGroup.m_def, repeats=True)

    def normalize(self, *args, **kwargs):
        super().normalize(*args, **kwargs)
        # this does not check if the plot was already stored
        self.figures.append(
            PlotlyFigure(
                label='Density of States',
                index=len(self.figures),
                figure=self.plot().to_plotly_json(),
            )
        )


class BandStructure(SemanticGroupContainer):
    k_path = SubSection(sub_section=KPoint.m_def, repeats=True)

    class BandGroup(SemanticGroup):

        class BandLabel(ProjectionTarget):  # ? necessary
            spin = SingleElectronSimpleSpin

        label = SubSection(subsection=BandLabel.m_def)

        energies = Quantity(
            type=np.float64,
            unit='J',
            shape=['*'],
            description='The eigenstate obtained from solving the electronic Schrödinger equation',  # ! re-word
        )

        def plot(self) -> go.Scatter:
            return go.Scatter(
                x=[k_point.k_point for k_point in self.m_parent.k_path],
                y=self.energies,
                mode='lines',
                name=self.name_from_section(),
                legend_group=self.label.plotly_legend_group(),
                legendgrouptitle_text=self.label.plotly_legend_group(),
                visible=False,
            )
        
    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        # this does not check if the plot was already stored
        self.figures.append(
            PlotlyFigure(
                label='Band Structure',
                index=len(self.figures),
                figure=self.plot().to_plotly_json(),
            )
        )


class KResolvedElectronicProperties(PlotSection, ModelBaseSection):
    """Collection section specialized in grouping together electronic properties defined by the k-space,
    e.g. electronic eigenvalues, band structure, density of states, etc.
    Due to the inconsistent nature of the Fermi level, we use `highest_occupied_state`, extracted from `eigenvalues`."""

    m_def = Section()

    fermi_region = SubSection(sub_section=FermiRegion.m_def)

    eigenvalues = SubSection(sub_section=KResolvedElectronicEigenvalues.m_def)

    dos = SubSection(sub_section=DensityOfStates.m_def)

    band_structure = SubSection(sub_section=BandStructure.m_def)


m_package.__init_metainfo__()
