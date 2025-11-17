from typing import TYPE_CHECKING

import numpy as np
import pint
from nomad.config import config
from nomad.metainfo import Quantity, SubSection

from nomad_simulations.schema_packages.variables import KLinePath

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    ElectronicState,
)
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap
from nomad_simulations.schema_packages.properties.electronic_eigenvalues import (
    ElectronicEigenvalues,
)
from nomad_simulations.schema_packages.properties.fermi_surface import FermiSurface
from nomad_simulations.schema_packages.utils import get_sibling_section, log

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class ElectronicBandStructure(ElectronicEigenvalues):
    """
    Accessible energies by the charges (electrons and holes) in the reciprocal space.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'

    k_path = SubSection(sub_section=KLinePath.m_def)

    reciprocal_cell = Quantity(
        type=KSpace.reciprocal_lattice_vectors,
        description="""
        Reciprocal lattice vectors associated with the k-space sampling used
        for these eigenvalues, taken from the corresponding `KSpace` numerical
        settings.
        """,
    )

    def resolve_reciprocal_cell(self) -> pint.Quantity | None:
        """
        Resolve the reciprocal cell from the `KSpace` numerical settings section.
        """
        numerical_settings = self.m_xpath(
            'm_parent.m_parent.model_method[-1].numerical_settings', dict=False
        )
        if numerical_settings is None:
            return None
        k_space = None
        for setting in numerical_settings:
            if isinstance(setting, KSpace):
                k_space = setting
                break
        if k_space is None:
            return None
        return k_space

    # TODO fix this method once `FermiSurface` property is implemented
    @log
    def extract_fermi_surface(self) -> FermiSurface | None:
        """
        Extract the Fermi surface for metallic systems using `FermiLevel.value`.
        """
        logger = self.extract_fermi_surface.__annotations__['logger']
        # Check if the system has a finite band gap
        homo, lumo = self.resolve_homo_lumo_eigenvalues()
        if (homo and lumo) and (lumo - homo).magnitude > 0:
            return None

        # Get the `fermi_level.value`
        fermi_level = get_sibling_section(
            section=self, sibling_section_name='fermi_level', logger=logger
        )
        if fermi_level is None:
            logger.warning(
                'Could not extract the `FermiSurface`, because `FermiLevel` is not stored.'
            )
            return None
        fermi_level_value = fermi_level.value.magnitude

        # Extract eigenvalues close to the `fermi_level.value`
        fermi_indices = np.logical_and(
            self.value.magnitude
            >= (fermi_level_value - configuration.fermi_surface_tolerance),
            self.value.magnitude
            <= (fermi_level_value + configuration.fermi_surface_tolerance),
        )
        fermi_values = self.value[fermi_indices]

        # Store `FermiSurface` values
        # ! This is still conceptually wrong: `value` should be the KMesh.points,
        # ! not the eigenvalues. Kept as-is until the FermiSurface property is final.
        fermi_surface = FermiSurface(
            n_bands=self.n_bands,
            is_derived=True,
            physical_property_ref=self,
        )
        fermi_surface.value = fermi_values
        return fermi_surface

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve reciprocal cell from the `KSpace` numerical settings section
        self.reciprocal_cell = self.resolve_reciprocal_cell()

        # TODO uncomment once `FermiSurface` property is implemented
        # fermi_surface = self.extract_fermi_surface(logger)
        # if fermi_surface is not None:
        #     self.m_parent.fermi_surfaces.append(fermi_surface)
