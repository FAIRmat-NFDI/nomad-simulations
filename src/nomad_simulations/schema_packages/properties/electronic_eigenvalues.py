from typing import TYPE_CHECKING

import numpy as np
import pint
from nomad.config import config
from nomad.metainfo import Quantity, SectionProxy, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import (
    ElectronicState,
)
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap
from nomad_simulations.schema_packages.properties.fermi_surface import FermiSurface
from nomad_simulations.schema_packages.utils import log
from nomad_simulations.schema_packages.variables import KLinePath, KPoints

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class BaseElectronicEigenvalues(PhysicalProperty):
    """
    A base section defining the quantities shared by the `ElectronicEigenvalues` and
    `ElectronicBandStructure` sibling properties. It carries no reciprocal-space axis and no
    normalize-time derivation: each sibling owns its axis (`k_points` for the full-zone sampling,
    `k_path` for the high-symmetry line path) and only `ElectronicEigenvalues` derives reference
    levels and the band gap.
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
        this quantity is defined as `[K.n_points, n_levels]`, where `K` is the reciprocal-space axis of the concrete
        sibling: `k_points` (`KPoints`) on `ElectronicEigenvalues` for a full Brillouin-zone sampling, or `k_path`
        (`KLinePath`) on `ElectronicBandStructure` for a high-symmetry path.
        """,
    )

    # NOTE (DRY): this highest-/lowest-occupied reference is intentionally mirrored in
    # specialized form elsewhere -- `ElectronicDensityOfStates.energies_origin` (DOS-refined).
    # The duplication is deliberate: each property keeps a source specialized for its own
    # derivation and plotting/visualization alignment.
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

    contributions = SubSection(
        sub_section=SectionProxy('BaseElectronicEigenvalues'),
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

    reciprocal_cell = Quantity(
        type=KSpace.reciprocal_lattice_vectors,
        description="""
        Reciprocal lattice vectors associated with the k-space sampling used
        for these eigenvalues, taken from the corresponding `KSpace` numerical
        settings.
        """,
    )

    def resolve_reciprocal_cell(self) -> 'KSpace | None':
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

        # Resolve reciprocal cell from the `KSpace` numerical settings section
        self.reciprocal_cell = self.resolve_reciprocal_cell()


class ElectronicEigenvalues(BaseElectronicEigenvalues):
    """
    Electronic eigenvalues sampled over the (possibly symmetry-reduced) Brillouin zone. The
    reciprocal-space axis is `k_points`, which stores the sampled coordinates directly and may
    carry integration `weights`. This sibling owns the derivation of the reference levels
    (`highest_occupied`, `lowest_unoccupied`) and of the electronic band gap, which require a
    full-zone sampling; eigenvalues along a high-symmetry path belong in
    `ElectronicBandStructure` instead.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicEigenvalues'

    k_points = SubSection(
        sub_section=KPoints.m_def,
        description="""
        Reciprocal-space points at which the eigenvalues are evaluated, stored directly in
        fractional coordinates, with optional Brillouin-zone integration `weights`.
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

    def is_metallic(self) -> bool:
        """
        Detect a metallic occupation pattern. A band crossing the Fermi level shows up either as
        partial occupations (beyond the occupation tolerance) or as a level that is filled at some
        k-points and empty at others. The detection is per-state and therefore does not require
        integration `weights`.

        Returns:
            (bool): Whether the occupation pattern is metallic. False if `occupation` is unset.
        """
        if self.occupation is None or len(self.occupation) == 0:
            return False
        occupation = np.asarray(self.occupation)
        max_occupation = 1.0 if self.spin_channel is not None else 2.0
        tolerance = configuration.occupation_tolerance

        # Partial occupations: a state that is neither filled nor empty
        filled = occupation >= max_occupation - tolerance
        empty = occupation <= tolerance
        if np.any(~filled & ~empty):
            return True

        # Band crossing: a level filled at some k-points and empty at others
        if occupation.ndim == 2:
            return bool(np.any(filled.any(axis=0) & empty.any(axis=0)))
        return False

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

    # TODO fix this method once `FermiSurface` property is implemented
    @log
    def extract_fermi_surface(self) -> FermiSurface | None:
        """
        Extract the Fermi surface for metallic systems, referenced to the highest occupied
        eigenvalue (`highest_occupied`), which coincides with the Fermi level for gapless systems.
        """
        logger = self.extract_fermi_surface.__annotations__['logger']
        # Check if the system has a finite band gap
        homo, lumo = self.resolve_homo_lumo_eigenvalues()
        if (homo is not None and lumo is not None) and (lumo - homo).magnitude > 0:
            return None

        # Use the highest occupied eigenvalue as the Fermi-level reference
        if homo is None:
            logger.warning(
                'Could not extract the `FermiSurface`: no `highest_occupied` eigenvalue available.'
            )
            return None
        fermi_level_value = homo.magnitude

        # Extract eigenvalues close to the Fermi-level reference
        fermi_indices = np.logical_and(
            self.value.magnitude
            >= (fermi_level_value - configuration.fermi_surface_tolerance),
            self.value.magnitude
            <= (fermi_level_value + configuration.fermi_surface_tolerance),
        )
        fermi_values = self.value[fermi_indices]

        # Store `FermiSurface` values
        # ! This is still conceptually wrong: `value` should be the k-points where the bands
        # ! cross the Fermi level, not the eigenvalues. Kept as-is until the FermiSurface
        # ! property is final.
        fermi_surface = FermiSurface(
            n_bands=self.n_levels,
            is_derived=True,
            physical_property_ref=self,
        )
        fermi_surface.value = fermi_values
        return fermi_surface

    def emit_band_gap(self) -> None:
        """
        Emit the derived `ElectronicBandGap` into the parent `Outputs.electronic_band_gaps`.
        Idempotent: emission is keyed on the archive path of the emitting property, so
        re-normalization (including after reload) does not duplicate the gap.
        """
        parent = self.m_parent
        if (
            parent is None
            or 'electronic_band_gaps' not in parent.m_def.all_sub_sections
        ):
            return
        for gap in parent.electronic_band_gaps:
            ref = gap.physical_property_ref
            if ref is not None and ref.m_path() == self.m_path():
                return
        band_gap = self.extract_band_gap()
        if band_gap is not None:
            parent.electronic_band_gaps.append(band_gap)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Derive the reference levels and the band gap, gated on a populated reciprocal-space
        sampling: without `k_points` the eigenvalues are not a Brillouin-zone sampling and no
        reference levels are derived, and for a metallic occupation pattern no gap exists.
        """
        super().normalize(archive, logger)

        if self.k_points is None or self.k_points.points is None:
            return
        if isinstance(self.k_points, KLinePath):
            # Mis-filed band structure: no reference levels from a path sampling.
            # `Outputs.normalize` promotes it to `ElectronicBandStructure`.
            return
        if self.is_metallic():
            return

        homo, lumo = self.resolve_homo_lumo_eigenvalues()
        if homo is not None and lumo is not None:
            self.highest_occupied = homo
            self.lowest_unoccupied = lumo
            self.emit_band_gap()


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
