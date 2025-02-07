import numpy as np
from nomad.config import config
from nomad.metainfo import (
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
    MEnum,
)
from nomad.metainfo.data_type import m_float64
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad_simulations.schema_packages.general import ModelBaseSection
from nomad_simulations.schema_packages.properties import energy
from nomad_simulations.schema_packages.atoms_state import OrbitalsState
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


class ProjectionTarget(ModelBaseSection, OrbitalsState):
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
        if self.l_quantum_symbol is not None:
            projected = True
            if self.n_quantum_number is not None:
                name += f' {self.n_quantum_number}{self.l_quantum_symbol}'
            else:
                name += f' {self.l_quantum_symbol}'
        return name if projected else 'total'


class m_unit64(m_float64):
    pass


class SemanticGroup(ModelBaseSection):
    """Group of electronic states with the same symmetry"""

    label = None

    def name_from_section(self) -> str:  # !
        return self.label.name_from_section()

    def plot(self) -> go.Scatter:
        """Generate an individual plotly plot."""
        pass


class SemanticGroupContainer(ModelBaseSection, PlotSection):
    """Container for semantic groups of electronic states"""  # ! re-word

    m_def = Section()

    groups = SubSection(sub_section=SemanticGroup.m_def, repeats=True)

    def plot(self) -> PlotlyFigure:
        figure = go.Figure()
        for group in self.groups:
            figure.add_trace(group.plot())
        return PlotlyFigure(figure=figure.to_plotly_json())

    def normalize(self, *args, **kwargs) -> None:
        super(ModelBaseSection, self).normalize(*args, **kwargs)
        super(PlotSection, self).normalize(*args, **kwargs)


class Frontiers(ModelBaseSection):
    """Frontiers of the electronic states"""

    highest_occupied_energy = energy.m_def.m_copy()

    lowest_unoccupied_energy = energy.m_def.m_copy()

    energy_gap = energy.m_def.m_copy()


class ElectronicEigenvalues(SemanticGroupContainer):
    """Eigenvalues of the electronic states"""

    class EigenvalueGroup(SemanticGroupContainer):
        class EigenvalueLabel(ProjectionTarget):  # ? necessary
            spin = SingleElectronSimpleSpin

        label = SubSection(sub_section=EigenvalueLabel.m_def)

        energies = Quantity(
            type=np.float64,
            unit='joule',
            shape=['*'],
            description='The eigenstate obtained from solving the electronic Schrödinger equation',  # ! re-word
        )

        occupations = Quantity(
            type=m_unit64,
            shape=['*'],
            description='Occupation of the states',
        )

    groups = SubSection(sub_section=EigenvalueGroup.m_def, repeats=True)


m_package.__init_metainfo__()
