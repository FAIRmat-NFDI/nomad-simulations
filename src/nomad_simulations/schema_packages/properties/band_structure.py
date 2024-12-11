from typing import TYPE_CHECKING, Optional, Union

import numpy as np
import pint
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.physical_properties import MaterialProperty, Count
from ..variables import SpinChannel, KMesh

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import AtomsState, OrbitalsState
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap

from nomad.config import config

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


Occupancy = Count.m_copy()  # ? establish semantic connection # values between 0 - 1 or 0 - 2
Occupancy.iri='http://fairmat-nfdi.eu/taxonomy/Occupancy',
Occupancy.description="""
Electrons occupancy of an atom per orbital and spin. This is a number defined between 0 and 1 for
spin-polarized systems, and between 0 and 2 for non-spin-polarized systems. This property is
important when studying if an orbital or spin channel are fully occupied, at half-filling, or
fully emptied, which have an effect on the electron-electron interaction effects.
"""


class ElectronicEigenstates(ArchiveSection):
    values = MaterialProperty(
        name='ElectronicEigenstates',
        fields=[Energy, Occupancy],  # shape defined by variables
        variables=[SpinChannel, KMesh],  # ? enforce spanned dimension at metainfo level
        iri='http://fairmat-nfdi.eu/taxonomy/ElectronicEigenvalues',
        description="""A base section used to define basic quantities for the `ElectronicEigenvalues`  and `ElectronicEigenstates` properties.""",
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
    )

    # ? Should we add functionalities to handle min/max of the `value` in some specific cases, e.g. bands around the Fermi level,
    # ? core bands separated by gaps, and equivalently, higher-energy valence bands separated by gaps?

    # references
    reciprocal_cell = Quantity(
        type=KSpace.reciprocal_lattice_vectors,
        description="""
        Reference to the reciprocal lattice vectors stored under `KSpace`.
        """,
    )  # !

    atoms_state_ref = Quantity(
        type=AtomsState,
        description="""
        Reference to the matching `AtomsState` section.
        """,
    )

    orbitals_state_ref = Quantity(
        type=OrbitalsState,
        description="""
        Reference to the matching `OrbitalsState` section.
        """,
    )  # ! TODO: unify with `atoms_state_ref`

    # derived properties
    n_bands = Quantity(
        type=np.int32,
        description="""
        Number of bands / eigenvalues.
        """,
    )  # ? remove

    highest_occupied = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Highest occupied electronic eigenvalue. Together with `lowest_unoccupied`, it defines the
        electronic band gap.
        """,
    )

    lowest_unoccupied = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        Lowest unoccupied electronic eigenvalue. Together with `highest_occupied`, it defines the
        electronic band gap.
        """,
    )

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


# TODO: consider matching different k-channels for indirect bandgaps
def bandstructure_to_dos(bs: ElectronicEigenstates) -> ElectronicDOS:
    pass

def dos_to_bandgap(dos: ElectronicDOS) -> ElectronicBandGap:
    pass
