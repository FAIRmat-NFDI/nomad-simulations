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
from ..base_sections import ModelBaseSection
from .common_properties import energy
from .molecular_electronics import (
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

    vbm = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Valence band maximum: the energy of the highest occupied state, similar to HOMO in a molecular setting.
        This value is used for alignment of various electronic structures.
        """,
    )

    cbm = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Conduction band minimum: the energy of the lowest unoccupied state, similar to LUMO in a molecular setting.
        This typically coincides with the conduction band minimum, barring any satellites.
        """,
    )

    fermi_level = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Classical definition of the Fermi level,
        as the middle between the valence band maximum and conduction band minimum.
        """,
    )

    band_gap = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        The energy difference between the conduction band minimum and the valence band maximum.
        `band_gap = None` (i.e. band gap not processed) is different here from `band_gap = 0` (no band gap, metallic system).
        """,
    )

    band_options = ['vbm', 'cbm', 'fermi_level']

    parsed_quantities = Quantity(
        type=MEnum(*band_options),
        shape=['*'],
        description='Quantities populated by the parser.',
    )

    def _register_parsed(self) -> list[str]:
        return [
            quantity.name
            for quantity in self.m_def.quantities
            if quantity.name in self.band_options
        ]

    def compute_band_gap(self) -> Optional[float]:
        try:
            return self.cbm - self.vbm
        except (TypeError, AttributeError):
            return None

    def compute_fermi_level(self) -> Optional[float]:
        try:
            return (self.cbm + self.vbm) / 2
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


def max_vbm(fermi_regions: list[FermiRegion]) -> Optional[float]:
    # what if some regions have no vbm?
    vbms = [fermi_region.vbm for fermi_region in fermi_regions]
    if len(vbms) > 0:
        return max(vbms)

def min_cbm(fermi_regions: list[FermiRegion]) -> Optional[float]:
    # what if some regions have no cbm?
    cbms = [fermi_region.cbm for fermi_region in fermi_regions]
    if len(cbms) > 0:
        return min(cbms)

def energy_shift(section) -> 'pint.Quantity':
    try:
        return (
            section.m_parent.fermi_region.vbm
            - section.fermi_region.vbm
        )
    except AttributeError:
        raise AttributeError('Cannot align plots: Fermi region not defined.')


class KResolvedElectronicEigenvalues(ElectronicEigenvalues):
    """Section containing information about electronic eigenvalues resolved in k-space."""

    fermi_region = SubSection(sub_section=FermiRegion.m_def)

    k_points = SubSection(sub_section=KPoint.m_def, repeats=True)

    class KResolvedEigenvalueGroup(ElectronicEigenvalues.EigenvalueGroup):

        fermi_region = SubSection(sub_section=FermiRegion.m_def)

    groups = SubSection(sub_section=KResolvedEigenvalueGroup.m_def, repeats=True)


class DensityOfStates(SemanticGroupContainer):
    """Section containing information about all band structure projections, and their combined plot."""

    fermi_region = SubSection(sub_section=FermiRegion.m_def)

    energies = Quantity(
        type=np.float64,
        unit='joule',
        shape=['*'],
        description='The energy of the collective electronic state.',
    )

    class DOSGroup(SemanticGroup):

        fermi_region = SubSection(sub_section=FermiRegion.m_def)  # deactivate normalization

        label = SubSection(sub_section=ProjectionTarget.m_def)

        values = Quantity(
            type=np.float64,
            # ? unit='1/J',
            shape=['*'],
            description='Density of states',
        )

        def plot(self) -> go.Scatter:
            return go.Scatter(
                x=(self.m_parent.energies + energy_shift(self.m_parent)).magnitude,  # ! check
                y=self.values,  #.magnitude,
                mode='lines',
                name=self.label.ms_quantum_symbol,
                legendgroup=self.label.name_from_section(),
                legendgrouptitle_text=self.label.name_from_section(),
            )

    groups = SubSection(sub_section=DOSGroup.m_def, repeats=True)

    def plot(self) -> PlotlyFigure:
        figure = super().plot()
        figure.label='Density of States'
        return figure
    
    def normalize(self, *args, **kwargs):
        super().normalize(*args, **kwargs)
        if not self.fermi_region:
            self.m_setdefault('fermi_region')
        if self.fermi_region.vbm is None:
            self.fermi_region.vbm = max_vbm(self.groups)
        if self.fermi_region.cbm is None:
            self.fermi_region.cbm = min_cbm(self.groups)
        self.fermi_region.normalize(*args, **kwargs)


class BandStructure(SemanticGroupContainer):
    """Section containing information about all band structure projections, and their combined plot."""

    fermi_region = SubSection(sub_section=FermiRegion.m_def)

    k_path = SubSection(sub_section=KPoint.m_def, repeats=True)

    class BandGroup(SemanticGroup):

        label = SubSection(sub_section=ProjectionTarget.m_def)

        fermi_region = SubSection(sub_section=FermiRegion.m_def)

        energies = Quantity(
            type=np.float64,
            unit='joule',
            shape=['*'],
            description='The energy of the collective electronic state.',
        )

        def plot(self) -> go.Scatter:
            return go.Scatter(
                x=[k_point.k_point for k_point in self.m_parent.k_path],  # ! TODO: pad out other k-points
                y=self.energies,
                mode='lines',
                name=self.label.ms_quantum_symbol,
                legendgroup=self.label.name_from_section(),
                legendgrouptitle_text=self.label.name_from_section(),
            )

    def plot(self) -> PlotlyFigure:
        figure = super().plot()
        figure.label='Band Structure'
        return figure
    
    def normalize(self, *args, **kwargs):
        super().normalize(*args, **kwargs)
        if not self.fermi_region:
            self.m_setdefault('fermi_region')
        if self.fermi_region.vbm is None:
            self.fermi_region.vbm = max_vbm(self.groups)
        if self.fermi_region.cbm is None:
            self.fermi_region.cbm = min_cbm(self.groups)
        self.fermi_region.normalize(*args, **kwargs)


class KResolvedElectronicProperties(ModelBaseSection):
    """
    Container section of electronic properties which may be aligned in the same k-space,
    e.g. electronic eigenvalues, band structure, density of states, etc.

    Due to the inconsistent application of the Fermi level definition across supported codes,
    we use the `vbm` instead. Both can be found under `fermi_region`.
    When not parsed, the `vbm` is extracted from

    1. `eigenvalues`
    2. `dos`
    3. `band_structure`
    """

    fermi_region = SubSection(sub_section=FermiRegion.m_def)  # ! deactivate normalization

    eigenvalues = SubSection(sub_section=KResolvedElectronicEigenvalues.m_def)

    dos = SubSection(sub_section=DensityOfStates.m_def)

    band_structure = SubSection(sub_section=BandStructure.m_def)

    def collect_vbm(self) -> tuple['pint.Quantity', 'Reference']:
        """Extract the valence band maximum from the available sections."""
        target_sections = (self.eigenvalues, self.dos, self.band_structure)
        vbms = [
            (prop.fermi_region.vbm, prop)
            for prop in target_sections
            if prop
            and prop.fermi_region
            and prop.fermi_region.vbm is not None
        ]
        return max(vbms, key=lambda x: x[0]) if vbms else ()

    def normalize(self, *args, **kwargs) -> None:
        super().normalize(*args, **kwargs)
        try:
            vbm, ref = self.collect_vbm()
            if not self.fermi_region:
                self.m_setdefault('fermi_region')
            if self.fermi_region.vbm is None:
                self.fermi_region.vbm = vbm
            self.fermi_region.normalized_from = ref
            self.fermi_region.normalize(*args, **kwargs)
        except ValueError:
            pass
        self.dos.figures.append(self.dos.plot())
        # band structure
