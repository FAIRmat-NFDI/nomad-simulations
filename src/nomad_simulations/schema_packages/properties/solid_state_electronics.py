import plotly.graph_objects as go
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pint

import numpy as np
from nomad.config import config
from nomad.metainfo import (
    Quantity,
    SchemaPackage,
    SubSection,
    MEnum,
    Reference,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad_simulations.schema_packages.general import ModelBaseSection
from nomad_simulations.schema_packages.properties import energy
from nomad_simulations.schema_packages.properties.molecular_electronics import (
    SingleElectronSimpleSpin,
    ProjectionTarget,
    SemanticGroup,
    SemanticGroupContainer,
    ElectronicEigenvalues,
)


configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)

m_package = SchemaPackage()


class KPoint(ModelBaseSection):
    """K-point in reciprocal space"""

    k_point = Quantity(
        type=np.float64,
        shape=['*'],
        unit='1/m',
        description='The k-point in reciprocal space',
    )

    high_symmetry_label = Quantity(
        type=str,  # ! MEnum
        description='High symmetry label of the k-point',
    )

    def name_from_section(self) -> str:
        return self.high_symmetry_label


class FermiRegion(ModelBaseSection):
    """
    Section describing the region around the Fermi level, up until the nearest bands.
    This region may be described either at a system-wide level, or for a subsystem.
    This is determined by the section containing the `FermiRegion` section.
    """

    valence_band_maximum = energy
    valence_band_maximum.description = """
    The energy of the highest occupied state, similar to HOMO in a molecular setting.
    This value is used for alignment of various electronic structures.
    """

    conduction_band_minimum = energy.m_def.m_copy()
    conduction_band_minimum.description = """
    The energy of the lowest unoccupied state, similar to LUMO in a molecular setting.
    This typically coincides with the conduction band minimum, barring any satellites.
    """

    fermi_level = energy.m_def.m_copy()
    fermi_level.description = """
    Classical definition of the Fermi level,
    as the middle between the valence band maximum and conduction band minimum.
    """

    band_gap = energy.m_def.m_copy()
    band_gap.description = """
    The energy difference between the conduction band minimum and the valence band maximum.
    `band_gap = None` (i.e. band gap not processed) is different here from `band_gap = 0` (no band gap, metallic system).
    """

    band_options = {
        'valence_band_maximum': 'vbm',
        'conduction_band_minimum': 'cbm',
        'fermi_level': 'fermi',
    }

    parsed_quantities = Quantity(
        type=MEnum(*band_options.values()),
        shape=['*'],
        description='Quantities populated by the parser.',
    )

    def _register_parsed(self) -> list[str]:
        registered_quantities: list[str] = []
        for quantity in self.m_def.quantities:
            if quantity.name in self.band_options:
                registered_quantities.append(self.band_options[quantity.name])
        return registered_quantities

    def compute_band_gap(self) -> Optional[float]:
        try:
            return self.conduction_band_minimum - self.valence_band_maximum
        except (TypeError, AttributeError):
            return None

    def compute_fermi_level(self) -> Optional[float]:
        try:
            return (self.conduction_band_minimum + self.valence_band_maximum) / 2
        except (TypeError, AttributeError):
            return None

    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        self.parsed_quantities = self._register_parsed()
        self.band_gap = (
            self.compute_band_gap() if self.band_gap is None else self.band_gap
        )
        self.fermi_level = (
            self.compute_fermi_level() if self.fermi_level is None else self.fermi_level
        )


class FermiRegionContainer(SemanticGroupContainer):
    fermi_region = SubSection(sub_section=FermiRegion.m_def)

    def max_vbm(self) -> float:
        return [group.fermi_region.valence_band_maximum for group in self.groups]

    def min_cbm(self) -> float:
        return [group.fermi_region.conduction_band_minimum for group in self.groups]

    def normalize(self, *arg, **kwargs) -> None:
        super().normalize(*arg, **kwargs)
        if self.fermi_region is None:
            self.fermi_region.m_setdefault(FermiRegion)
        if self.fermi_region.valence_band_maximum is None:
            self.fermi_region.valence_band_maximum = max(self.max_vbm)
        if self.fermi_region.conduction_band_minimum is None:
            self.fermi_region.conduction_band_minimum = min(self.min_cbm)
        self.fermi_region.normalize(*arg, **kwargs)


class KResolvedElectronicEigenvalues(ElectronicEigenvalues, FermiRegionContainer):
    k_point = SubSection(sub_section=KPoint.m_def)

    class KResolvedEigenvalueGroup(
        ElectronicEigenvalues.EigenvalueGroup, FermiRegionContainer
    ):
        pass

    groups = SubSection(sub_section=KResolvedEigenvalueGroup.m_def, repeats=True)


class ReferencedFermiRegionContainer(FermiRegionContainer):
    def energy_shift(self) -> 'pint.Quantity':
        try:
            return (
                self.m_parent.fermi_region.valence_band_maximum
                - self.fermi_region.valence_band_maximum
            )
        except AttributeError:
            raise AttributeError('Cannot align plots: Fermi region not defined.')


class DensityOfStates(ReferencedFermiRegionContainer):
    energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['*'],
        description='The eigenstate obtained from solving the electronic Schrödinger equation',  # ! re-word
    )

    class DOSGroup(SemanticGroup):
        class DOSLabel(ProjectionTarget):
            spin = SingleElectronSimpleSpin

        label = SubSection(sub_section=DOSLabel.m_def)

        values = Quantity(
            type=np.float64,
            # ? unit='1/J',
            shape=['*'],
            description='Density of states',
        )

        def plot(self) -> go.Scatter:
            return go.Scatter(
                x=(self.m_parent.energies + self.m_parent.energy_shift()).magnitude,  # ! check
                y=self.values,  #.magnitude,
                mode='lines',
                name=self.label.spin,
                legendgroup=self.label.name_from_section(),
                legendgrouptitle_text=self.label.name_from_section(),
            )

    groups = SubSection(sub_section=DOSGroup.m_def, repeats=True)

    def plot(self) -> PlotlyFigure:
        figure = super().plot()
        figure.label='Density of States'
        return figure


class BandStructure(ReferencedFermiRegionContainer):
    k_path = SubSection(sub_section=KPoint.m_def, repeats=True)

    class BandGroup(SemanticGroup):
        class BandLabel(ProjectionTarget):  # ? necessary
            spin = SingleElectronSimpleSpin

        label = SubSection(sub_section=BandLabel.m_def)

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


class KResolvedElectronicProperties(ModelBaseSection):
    """
    Collection section specialized in grouping together electronic properties defined by the k-space,
    e.g. electronic eigenvalues, band structure, density of states, etc.
    Due to the inconsistent nature of the Fermi level, we use `highest_occupied_state`, extracted from `eigenvalues`.
    """

    fermi_region = SubSection(sub_section=FermiRegion.m_def)

    eigenvalues = SubSection(sub_section=KResolvedElectronicEigenvalues.m_def)

    dos = SubSection(sub_section=DensityOfStates.m_def)

    band_structure = SubSection(sub_section=BandStructure.m_def)

    def collect_vbm(self) -> tuple['pint.Quantity', 'Reference']:
        target_sections = (self.eigenvalues, self.dos, self.band_structure)
        vbms = [
            (prop.fermi_region.valence_band_maximum, prop)
            for prop in target_sections
            if prop
            and prop.fermi_region
            and prop.fermi_region.valence_band_maximum is not None
        ]
        return max(vbms, key=lambda x: x[0]) if vbms else ()

    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        try:
            vbm, ref = self.collect_vbm()
            self.m_setdefault('fermi_region')
            self.fermi_region.valence_band_maximum = vbm
            self.fermi_region.normalized_from = ref
            # ? normalize fermi region
        except ValueError:
            pass
        self.dos.figures.append(self.dos.plot())


m_package.__init_metainfo__()
