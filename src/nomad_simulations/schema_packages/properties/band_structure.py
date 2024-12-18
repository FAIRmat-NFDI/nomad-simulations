from typing import TYPE_CHECKING, Optional, Union

import numpy as np
import pint

from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from ..variables import SpinChannel, KPoint, ElectronicEigenEnergies

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap

from nomad.config import config

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class ElectronicEigenEnergiesSection(ArchiveSection):
    electronic_eigen_energies = ElectronicEigenEnergies()

    highest_occupied = Energy()  # ? C4: remove

    lowest_unoccupied = Energy()  # ? C4: remove

    # ? Should we add functionalities to handle min/max of the `value` in some specific cases, e.g. bands around the Fermi level,
    # ? core bands separated by gaps, and equivalently, higher-energy valence bands separated by gaps?

    def order_eigenvalues(self) -> Union[bool, tuple['pint.Quantity', np.ndarray]]:
        """
        Order the eigenvalues based on the `value` and `occupation`. The return `value` and
        `occupation` are flattened.
        """
        total_shape = np.prod(self.value.shape)

        # Order the indices in the flattened list of `value`
        flattened_value = self.value.reshape(total_shape)
        flattened_occupation = self.occupation.reshape(total_shape)
        sorted_indices = np.argsort(flattened_value, axis=0)

        sorted_value = (
            np.take_along_axis(flattened_value.magnitude, sorted_indices, axis=0)
            * flattened_value.u
        )
        sorted_occupation = np.take_along_axis(
            flattened_occupation, sorted_indices, axis=0
        )
        self.m_cache['sorted_eigenvalues'] = True
        return sorted_value, sorted_occupation

    def resolve_homo_lumo_eigenvalues(
        self,
    ) -> tuple[Optional['pint.Quantity'], Optional['pint.Quantity']]:
        """
        Resolve the `highest_occupied` and `lowest_unoccupied` eigenvalues by performing a binary search on the
        flattened and sorted `value` and `occupation`. If these quantities already exist, overwrite them or return
        them if it is not possible to resolve from `value` and `occupation`.
        """
        # Sorting `value` and `occupation`
        if not self.order_eigenvalues():  # validation fails
            if self.highest_occupied is not None and self.lowest_unoccupied is not None:
                return self.highest_occupied, self.lowest_unoccupied
            return None, None
        sorted_value, sorted_occupation = self.order_eigenvalues()
        sorted_value_unit = sorted_value.u
        sorted_value = sorted_value.magnitude

        # Binary search ot find the transition point between `occupation = 2` and `occupation = 0`
        homo = self.highest_occupied
        lumo = self.lowest_unoccupied
        mid = (
            np.searchsorted(
                sorted_occupation <= configuration.occupation_tolerance, True
            )
            - 1
        )
        if mid >= 0 and mid < len(sorted_occupation) - 1:
            if sorted_occupation[mid] > 0 and (
                sorted_occupation[mid + 1] >= -configuration.occupation_tolerance
                and sorted_occupation[mid + 1] <= configuration.occupation_tolerance
            ):
                homo = sorted_value[mid] * sorted_value_unit
                lumo = sorted_value[mid + 1] * sorted_value_unit

        return homo, lumo

    def extract_band_gap(self) -> Optional['ElectronicBandGap']:
        """
        Extract the electronic band gap from the `highest_occupied` and `lowest_unoccupied` eigenvalues.
        If the difference of `highest_occupied` and `lowest_unoccupied` is negative, the band gap `value` is set to 0.0.
        """
        band_gap = None
        homo, lumo = self.resolve_homo_lumo_eigenvalues()
        if homo and lumo:
            band_gap = ElectronicBandGap(is_derived=True, physical_property_ref=self)

            if (lumo - homo).magnitude < 0:
                band_gap.value = 0.0
            else:
                band_gap.value = lumo - homo
        return band_gap

    def resolve_reciprocal_cell(self) -> Optional['pint.Quantity']:
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve `highest_occupied` and `lowest_unoccupied` eigenvalues
        self.highest_occupied, self.lowest_unoccupied = (
            self.resolve_homo_lumo_eigenvalues()
        )

        # `ElectronicBandGap` extraction
        band_gap = self.extract_band_gap()
        if band_gap is not None:
            self.m_parent.electronic_band_gaps.append(band_gap)

        # Resolve `reciprocal_cell` from the `KSpace` numerical settings section
        self.reciprocal_cell = self.resolve_reciprocal_cell()


class BandStructure(ArchiveSection):
    values = DatasetTemplate(
        name='BandStructure',
        fields=[ElectronicEigenstates.values],
        variables=[KMesh],  # ? at what level will `SpinChannel` exist
    )

    kind = Quantity(
        type=MEnum('KS', 'KSxc', 'SigX', 'SigC', 'Zk'),
        description="""
        Contributions to the electronic eigenvalues. Example, in the case of a DFT+GW calculation, the GW eigenvalues
        are stored under `value`, and each contribution is identified by `label`:
            - `'KS'`: Kohn-Sham contribution. This is also stored in the DFT entry under `ElectronicEigenvalues.value`.
            - `'KSxc'`: Diagonal matrix elements of the expectation value of the Kohn-Sahm exchange-correlation potential.
            - `'SigX'`: Diagonal matrix elements of the exchange self-energy. This is also stored in the GW entry under `ElectronicSelfEnergy.value`.
            - `'SigC'`: Diagonal matrix elements of the correlation self-energy. This is also stored in the GW entry under `ElectronicSelfEnergy.value`.
            - `'Zk'`: Quasiparticle renormalization factors contribution. This is also stored in the GW entry under `QuasiparticleWeights.value`.
        """,
    )  # ? move to `ElectronicEigenstates`

    reciprocal_cell = Quantity(
        type=KSpace.reciprocal_lattice_vectors,
        description="""
        Reference to the reciprocal lattice vectors stored under `KSpace`.
        """,
    )  # !

    highest_occupied = DatasetTemplate(
        name='HighestOccupied',
        mandatory_fields=[Energy, KMesh],
    )  # ? property

    lowest_unoccupied = ighest_occupied = DatasetTemplate(
        name='LowestUnoccupied',
        mandatory_fields=[Energy, KMesh],
    )  # ? property

    # ! plot
