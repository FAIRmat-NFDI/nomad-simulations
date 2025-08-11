from typing import TYPE_CHECKING

import numpy as np
import pint
from nomad.config import config
from nomad.metainfo import Quantity, SubSection

from nomad_simulations.schema_packages.numerical_settings import KMesh

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import AtomsState, OrbitalsState
from nomad_simulations.schema_packages.data_types import unit_float
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.utils.utils import check_not_none, inner_copy

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class BaseElectronicEigenvalues(PhysicalProperty):
    """
    A base section used to define basic quantities for the `ElectronicEigenvalues`  and `ElectronicBandStructure` properties.
    """

    n_bands = Quantity(
        type=np.int32,
        description="""
        Number of bands / eigenvalues.
        """,
    )  # TODO: remove


class ElectronicEigenvalues(BaseElectronicEigenvalues):
    """ """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicEigenvalues'

    # TODO: add spin annotation from @EBB2675

    value = Quantity(
        type=np.float64,
        unit='joule',
        shape=['spin', 'level'],
        description="""
        Value of the electronic eigenvalues.
        Dimensions: [spin channel, energy level].
        """,
    )

    occupation = Quantity(
        type=unit_float(dtype=np.float64),
        shape=['spin', 'level'],
        description="""
        Occupation of the electronic eigenvalues, ranging from 0 to 1.
        Dimensions: [spin channel, energy level].
        """,
    )  # restructure spin for plotting?

    highest_occupied = Quantity(
        type=np.float64,
        shape=['spin'],
        unit='joule',
        description="""
        Highest occupied electronic eigenvalue for each spin channel. Together with `lowest_unoccupied`, it defines the
        electronic band gap. Automatically resolved using binary search on sorted eigenvalues.
        """,
    )

    lowest_unoccupied = Quantity(
        type=np.float64,
        shape=['spin'],
        unit='joule',
        description="""
        Lowest unoccupied electronic eigenvalue for each spin channel. Together with `highest_occupied`, it defines the
        electronic band gap. Automatically resolved using binary search on sorted eigenvalues.
        """,
    )

    value_contributions = SubSection(
        sub_section=BaseElectronicEigenvalues.m_def,
        repeats=True,
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

    @check_not_none('self.value', 'self.occupation')
    def resolve_homo_lumo(self) -> None:
        """
        Resolve HOMO and LUMO eigenvalues using binary search on sorted eigenvalues.
        """

        def process_spin_channel(data: np.ndarray) -> list:
            """Process a single spin channel to find HOMO/LUMO."""
            mid = int(len(data) / 2)  # ? extra check
            values, occupations = data[:mid], data[mid:]
            lumo_region = np.where(occupations <= 1e-6)

            if lumo_region[0].size > 0:
                lumo_idx = np.min(lumo_region)
                if lumo_idx > 0:
                    return [values[lumo_idx - 1], values[lumo_idx]]  # [HOMO, LUMO]
                else:
                    return [np.nan, values[lumo_idx]]
            else:
                return [np.nan, np.nan]

        # Stack value and occupation arrays along last axis for apply_along_axis
        combined_data = np.stack([self.value.magnitude, self.occupation], axis=-1)
        results = np.apply_along_axis(process_spin_channel, axis=0, arr=combined_data.T)

        self.highest_occupied = results[:, 0] * self.value.u
        self.lowest_unoccupied = results[:, 1] * self.value.u

    def pad_out(self) -> None:
        """
        Pad out the value and occupation arrays along the spin channel dimension.
        """
        spin_index = 0  # Spin is now first dimension
        if (
            np.array(self.value).shape[spin_index] == 1
        ):  # TODO: add model_method spin_polarized
            self.value = inner_copy(self.value, 0)  # TODO: dynamically set repetition
        if (
            np.array(self.occupation).shape[spin_index] == 1
        ):  # TODO: add model_method spin_polarized
            self.occupation = inner_copy(
                self.occupation, 0
            )  # TODO: dynamically set repetition

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.pad_out()
        self.resolve_homo_lumo()


class ElectronicBandStructure(BaseElectronicEigenvalues):
    """
    Accessible energies by the charges (electrons and holes) in the reciprocal space.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'

    kpoint = SubSection(sub_section=KMesh.m_def)

    value = Quantity(
        type=np.float64,
        unit='joule',
        shape=['spin', 'kpoint', 'level'],
        description="""
        Value of the electronic eigenvalues in the reciprocal space.
        Dimensions: [spin channel, k-point, energy level].
        """,
    )

    occupation = Quantity(
        type=unit_float(dtype=np.float64),
        shape=['spin', 'kpoint', 'level'],
        description="""
        Occupation of the electronic eigenvalues, ranging from 0 to 1.
        Dimensions: [spin channel, k-point, energy level].
        """,
    )

    highest_occupied = Quantity(
        type=np.float64,
        shape=['spin', 'kpoint'],
        unit='joule',
        description="""
        Highest occupied electronic eigenvalue for each k-point and spin channel. Together with `lowest_unoccupied`, it defines the
        electronic band gap. Automatically resolved using binary search on sorted eigenvalues.
        """,
    )

    lowest_unoccupied = Quantity(
        type=np.float64,
        shape=['spin', 'kpoint'],
        unit='joule',
        description="""
        Lowest unoccupied electronic eigenvalue for each k-point and spin channel. Together with `highest_occupied`, it defines the
        electronic band gap. Automatically resolved using binary search on sorted eigenvalues.
        """,
    )

    @check_not_none('self.value', 'self.occupation')
    def resolve_homo_lumo(self) -> None:
        """
        Resolve HOMO and LUMO eigenvalues using binary search on sorted eigenvalues for band structure.
        """

        def process_spin_kpoint(data: np.ndarray) -> list:
            """Process a single k-point and spin channel to find HOMO/LUMO."""
            mid = int(len(data) / 2)  # ? extra check
            values, occupations = data[:mid], data[mid:]
            lumo_region = np.where(occupations <= 1e-6)

            if lumo_region[0].size > 0:
                lumo_idx = np.min(lumo_region)
                if lumo_idx > 0:
                    return [values[lumo_idx - 1], values[lumo_idx]]  # [HOMO, LUMO]
                else:
                    return [np.nan, values[lumo_idx]]
            else:
                return [np.nan, np.nan]

        n_spins, n_kpoints, n_levels = self.value.shape

        # Stack along last axis to get [n_spins, n_kpoints, n_levels, 2]
        combined_data = np.stack([self.value.magnitude, self.occupation], axis=2)
        reshaped_data = combined_data.reshape(n_spins * n_kpoints, n_levels * 2)

        results = np.apply_along_axis(process_spin_kpoint, axis=1, arr=reshaped_data)
        results = results.reshape(n_spins, n_kpoints, 2)

        self.highest_occupied = results[:, :, 0] * self.value.u
        self.lowest_unoccupied = results[:, :, 1] * self.value.u

    def pad_out(self) -> None:
        """
        Pad out the value and occupation arrays along the spin channel dimension.
        """
        spin_index = 0
        if self.value.shape[spin_index] == 1:  # TODO: add model_method spin_polarized
            self.value = inner_copy(self.value, 0)  # TODO: dynamically set repetition
        if (
            self.occupation.shape[spin_index] == 1
        ):  # TODO: add model_method spin_polarized
            self.occupation = inner_copy(
                self.occupation, 0
            )  # TODO: dynamically set repetition

    def resolve_reciprocal_cell(self) -> pint.Quantity | None:  # ? remove
        """
        Resolve the reciprocal cell from the `KSpace` numerical settings section.

        Returns:
            Optional[pint.Quantity]: _description_
        """
        numerical_settings = self.m_xpath(
            'm_parent.m_parent.model_method[-1].numerical_settings', dict=False
        )
        if numerical_settings is None:
            return None

        for setting in numerical_settings:
            if isinstance(setting, KSpace):
                return setting

    def resolve_kpoints_from_kspace(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Search for KSpace in archive.data.model_methods[..].numerical_settings[..] 
        and set it to ElectronicBandStructure.kpoints using xpath.
        """
        # Search for KSpace objects in all model_methods numerical_settings
        kspace_objects = archive.m_xpath(
            'data.model_method[*].numerical_settings[*].k_mesh', dict=False
        )
        
        if kspace_objects is None:
            logger.warning(
                'No KSpace object found in numerical_settings, cannot resolve `ElectronicBandStructure.kpoint`.'
            )
            return
        elif len(kspace_objects) > 1:
            logger.warning(
                'Multiple KSpace objects found in numerical_settings, cannot resolve `ElectronicBandStructure.kpoint`.'
            )
            return

        self.kpoint = kspace_objects[0][0][0]

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.pad_out()
        self.resolve_homo_lumo()
        self.resolve_kpoints_from_kspace(archive, logger)


# defunct
class Occupancy(PhysicalProperty):
    """
    Electrons occupancy of an atom per orbital and spin. This is a number defined between 0 and 1 for
    spin-polarized systems, and between 0 and 2 for non-spin-polarized systems. This property is
    important when studying if an orbital or spin channel are fully occupied, at half-filling, or
    fully emptied, which have an effect on the electron-electron interaction effects.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/Occupancy'

    atoms_state_ref = Quantity(
        type=AtomsState,
        description="""
        Reference to the `AtomsState` section in which the occupancy is calculated.
        """,
    )

    orbitals_state_ref = Quantity(
        type=OrbitalsState,
        description="""
        Reference to the `OrbitalsState` section in which the occupancy is calculated.
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
        Value of the electronic occupancy in the atom defined by `atoms_state_ref` and the orbital
        defined by `orbitals_state_ref`. the orbital. If `spin_channel` is set, then this number is
        between 0 and 1, where 0 means that the state is unoccupied and 1 means that the state is
        fully occupied; if `spin_channel` is not set, then this number is between 0 and 2.
        """,
    )
