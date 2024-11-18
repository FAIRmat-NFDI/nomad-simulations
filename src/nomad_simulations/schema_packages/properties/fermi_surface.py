from typing import TYPE_CHECKING, Optional

import numpy as np
from nomad.metainfo import Quantity

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.utils import get_sibling_section


from nomad.config import config
configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


# TODO fix this method once `FermiSurface` property is implemented
def extract_fermi_surface(self, logger: 'BoundLogger') -> Optional['FermiSurface']:
    """
    Extract the Fermi surface for metal systems and using the `FermiLevel.value`.

    Args:
        logger (BoundLogger): The logger to log messages.

    Returns:
        (Optional[FermiSurface]): The extracted Fermi surface section to be stored in `Outputs`.
    """
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

    # Extract values close to the `fermi_level.value`
    fermi_indices = np.logical_and(
        self.value.magnitude
        >= (fermi_level_value - configuration.fermi_surface_tolerance),
        self.value.magnitude
        <= (fermi_level_value + configuration.fermi_surface_tolerance),
    )
    fermi_values = self.value[fermi_indices]

    # Store `FermiSurface` values
    # ! This is wrong (!) the `value` should be the `KMesh.points`, not the `ElectronicEigenvalues.value`
    fermi_surface = FermiSurface(
        n_bands=self.n_bands,
        is_derived=True,
        physical_property_ref=self,
    )
    fermi_surface.variables = self.variables
    fermi_surface.value = fermi_values
    return fermi_surface

# TODO This class is not implemented yet. @JosePizarro3 will work in another PR to implement it.
class FermiSurface(PhysicalProperty):
    """
    Energy boundary in reciprocal space that separates the filled and empty electronic states in a metal.
    It is related with the crossing points in reciprocal space by the chemical potential or, equivalently at
    zero temperature, the Fermi level.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/FermiSurface'

    n_bands = Quantity(
        type=np.int32,
        description="""
        Number of bands / eigenvalues.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        # ! `n_bands` need to be set up during initialization of the class
        self.rank = [int(kwargs.get('n_bands'))]
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
