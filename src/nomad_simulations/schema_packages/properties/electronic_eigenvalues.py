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
    ElectronicState,
)
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap
from nomad_simulations.schema_packages.utils import get_sibling_section, log

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class BaseElectronicEigenvalues(PhysicalProperty):
    """
    A base section used to define basic quantities for the `ElectronicEigenvalues`  and `ElectronicBandStructure` properties.
    """

    n_levels = Quantity(
        type=np.int32,
        description="""
        Number of energy levels per sampling point.

        In periodic systems these correspond to electronic bands; in molecular
        calculations they correspond to (spin-resolved) molecular orbitals or
        similar one-particle states.
        """,
    )

    value = Quantity(
        type=np.float64,
        unit='joule',
        shape=['*', '*'],
        description="""
        Value of the electronic eigenvalues.
        """,
    )


class ElectronicEigenvalues(BaseElectronicEigenvalues):
    """ """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicEigenvalues'

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic eigenvalues. It can take values of 0 or 1.
        """,
    )

    occupation = Quantity(
        type=np.float64,
        shape=['*', 'n_levels'],
        description="""
        Occupation of the electronic eigenvalues. This is a number depending whether the `spin_channel` has been set or not.
        If `spin_channel` is set, then this number is between 0 and 1, where 0 means that the state is unoccupied and 1 means
        that the state is fully occupied; if `spin_channel` is not set, then this number is between 0 and 2. The shape of
        this quantity is defined as `[K.n_points, K.dimensionality, n_levels]`, where `K` is a `variable` which can
        be `KMesh` or `KLinePath`, depending whether the simulation mapped the whole Brillouin zone or just a specific
        path.
        """,
    )

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

    # ? Should we add functionalities to handle min/max of the `value` in some specific cases, .e.g, bands around the Fermi level,
    # ? core bands separated by gaps, and equivalently, higher-energy valence bands separated by gaps?

    value_contributions = SubSection(
        sub_section=BaseElectronicEigenvalues.m_def,
        repeats=True,
        description="""
        Contributions to the electronic eigenvalues. Example, in the case of a DFT+GW calculation, the GW eigenvalues
        are stored under `value`, and each contribution is identified by `label`:
            - `'KS'`: Kohn-Sham contribution. This is also stored in the DFT entry under `ElectronicEigenvalues.value`.
            - `'KSxc'`: Diagonal matrix elements of the expectation value of the Kohn-Sham exchange-correlation potential.
            - `'SigX'`: Diagonal matrix elements of the exchange self-energy. This is also stored in the GW entry under `ElectronicSelfEnergy.value`.
            - `'SigC'`: Diagonal matrix elements of the correlation self-energy. This is also stored in the GW entry under `ElectronicSelfEnergy.value`.
            - `'Zk'`: Quasiparticle renormalization factors contribution. This is also stored in the GW entry under `QuasiparticleWeights.value`.
        """,
    )

    def order_eigenvalues(self) -> tuple[pint.Quantity, np.ndarray] | None:
        """
        Order the eigenvalues based on the `value` and `occupation`. The return `value` and
        `occupation` are flattened.

        Returns:
            (tuple[pint.Quantity, np.ndarray] | tuple[()]): The flattened and sorted `value` and `occupation`. If validation
            fails, then it returns an empty tuple.
        """
        # Validation: check if both value and occupation exist and have same shape
        if self.value is None or self.occupation is None:
            return None
        if self.value.shape != self.occupation.shape:
            return None

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
    ) -> tuple[pint.Quantity | None, pint.Quantity | None]:
        """
        Resolve the `highest_occupied` and `lowest_unoccupied` eigenvalues by performing a binary search on the
        flattened and sorted `value` and `occupation`. If these quantities already exist, overwrite them or return
        them if it is not possible to resolve from `value` and `occupation`.

        Returns:
            (tuple[Optional[pint.Quantity], Optional[pint.Quantity]]): The `highest_occupied` and
            `lowest_unoccupied` eigenvalues.
        """
        # Sorting `value` and `occupation`
        ordered_results = self.order_eigenvalues()
        if ordered_results is not None:
            sorted_value, sorted_occupation = ordered_results
            sorted_value_unit = sorted_value.u
            sorted_value = sorted_value.magnitude
        else:
            if self.highest_occupied is not None and self.lowest_unoccupied is not None:
                return self.highest_occupied, self.lowest_unoccupied
            return None, None

        # Binary search to find the transition point between `occupation = 2` and `occupation = 0`
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

    def extract_band_gap(self) -> ElectronicBandGap | None:
        """
        Extract the electronic band gap from the `highest_occupied` and `lowest_unoccupied` eigenvalues.
        If the difference of `highest_occupied` and `lowest_unoccupied` is negative, the band gap `value` is set to 0.0.

        Returns:
            (Optional[ElectronicBandGap]): The extracted electronic band gap section to be stored in `Outputs`.
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


class Occupancy(PhysicalProperty):
    """
    Electrons occupancy of an atom per orbital and spin. This is a number defined between 0 and 1 for
    spin-polarized systems, and between 0 and 2 for non-spin-polarized systems. This property is
    important when studying if an orbital or spin channel are fully occupied, at half-filling, or
    fully emptied, which have an effect on the electron-electron interaction effects.

    The `orbitals_state_ref` field points to an `ElectronicState` describing the orbital. To access
    the parent AtomsState, use `orbitals_state_ref.get_parent_entity()`. This follows the
    ElectronicState gateway pattern.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/Occupancy'

    orbitals_state_ref = Quantity(
        type=ElectronicState,
        description="""
        Reference to the `ElectronicState` section in which the occupancy is calculated.
        This can reference individual orbitals, orbital manifolds, or hybrid/molecular orbitals.
        The parent AtomsState can be accessed via `orbitals_state_ref.get_parent_entity()`.
        """,
    )

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic property. It can take values of 0 and 1.
        """,
    )

    value = Quantity(
        type=np.float64,
        description="""
        Value of the electronic occupancy for the orbital defined by `orbitals_state_ref`.
        If `spin_channel` is set, then this number is between 0 and 1, where 0 means that
        the state is unoccupied and 1 means that the state is fully occupied; if `spin_channel`
        is not set, then this number is between 0 and 2.
        """,
    )

    # TODO add extraction from `ElectronicEigenvalues.occupation`
