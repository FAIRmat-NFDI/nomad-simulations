from typing import TYPE_CHECKING

import numpy as np
from nomad.metainfo import Quantity

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.data_types import positive_float
from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class ElectronicBandGap(PhysicalProperty):
    """
    Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap'

    value = Quantity(
        type=positive_float(),
        unit='joule',
        description="""
        The value of the electronic band gap. This value must be positive.
        `None` indicates that no band gap could be determined, e.g., if the system is metallic.
        """,
    )

    momentum_transfer = Quantity(
        type=np.float64,
        unit='1/meter',
        description="""
        The length of the difference in reciprocal space between the initial and final momentum transfer
        along which the electronic band gap is defined.
        
        Example, the momentum transfer in bulk Si2 happens between the Γ and (approximately) X points, thus:
            `momentum_transfer = ||[0, 0, 0] - [0.5, 0.5, 0]|| ~= 0.612`.
        """,
    )

    # TODO: give it a place
    def extract_band_gap(self) -> 'ElectronicBandGap | None':
        """
        Extract the electronic band gap from the `highest_occupied_energy` and `lowest_unoccupied_energy` stored
        in `m_cache` from `resolve_energies_origin()`. If the difference of `highest_occupied_energy` and
        `lowest_unoccupied_energy` is negative, the band gap `value` is set to 0.0.

        Returns:
            (Optional[ElectronicBandGap]): The extracted electronic band gap section to be stored in `Outputs`.
        """
        band_gap = None
        homo = self.m_cache.get('highest_occupied_energy')
        lumo = self.m_cache.get('lowest_unoccupied_energy')
        if homo and lumo:
            band_gap = ElectronicBandGap()
            band_gap.is_derived = True
            band_gap.physical_property_ref = self

            if (homo - lumo).magnitude < 0:
                band_gap.value = 0.0
            else:
                band_gap.value = homo - lumo
        return band_gap
