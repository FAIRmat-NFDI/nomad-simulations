from typing import TYPE_CHECKING, Optional

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
from nomad_simulations.schema_packages.utils.utils import check_not_none
from nomad_simulations.schema_packages.utils.electronic import quicksearch_first_value, inner_copy

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
        shape=['level', 'spin'],
        description="""
        Value of the electronic eigenvalues.
        Rows correspond to the energy levels, and columns correspond to the spin channels.
        """,
    )

    occupation = Quantity(
        type=unit_float(),
        shape=['level', 'spin'],
        description="""
        Occupation of the electronic eigenvalues, ranging from 0 to 1.
        Rows correspond to the energy levels, and columns correspond to the spin channels.
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
        def process_spin_channel(spin_data):
            """Process a single spin channel to find HOMO/LUMO."""
            spin_values, spin_occupations = spin_data
            lumo_idx = quicksearch_first_value(
                spin_occupations, 0.0, tolerance=1e-6
            )

            return [
                spin_values[lumo_idx] if lumo_idx is not None and lumo_idx >= 0 else None,
                spin_values[lumo_idx + 1] if lumo_idx is not None and lumo_idx > 0 else None
            ]

        # Stack value and occupation arrays along last axis for apply_along_axis
        combined_data = np.stack([self.value, self.occupation.magnitude], axis=-1)
        results = np.apply_along_axis(process_spin_channel, axis=0, arr=combined_data.T)
        
        self.highest_occupied = results[:, 0] * self.value.u
        self.lowest_unoccupied = results[:, 1] * self.value.u

    def pad_out(self) -> None:
        """
        Pad out the value and occupation arrays along the spin channel dimension.
        """
        spin_index = 2
        if np.array(self.value).shape[spin_index] == 1:  # TODO: add model_method spin_polarized
            self.value = inner_copy(self.value, 0)  # TODO: dynamically set repetition
        if np.array(self.occupation).shape[spin_index] == 1:  # TODO: add model_method spin_polarized
            self.occupation = inner_copy(self.occupation, 0)  # TODO: dynamically set repetition

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
        shape=['level', 'kpoint', 'spin'],
        description="""
        Value of the electronic eigenvalues in the reciprocal space.
        Dimensions: [energy level, k-point, spin channel].
        """,
    )

    occupation = Quantity(
        type=unit_float(),
        shape=['level', 'kpoint', 'spin'],
        description="""
        Occupation of the electronic eigenvalues, ranging from 0 to 1.
        Dimensions: [energy level, k-point, spin channel].
        """,
    )

    highest_occupied = Quantity(
        type=np.float64,
        shape=['kpoint', 'spin'],
        unit='joule',
        description="""
        Highest occupied electronic eigenvalue for each k-point and spin channel. Together with `lowest_unoccupied`, it defines the
        electronic band gap. Automatically resolved using binary search on sorted eigenvalues.
        """,
    )

    lowest_unoccupied = Quantity(
        type=np.float64,
        shape=['kpoint', 'spin'],
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
        def process_kpoint_spin(kpoint_spin_data):
            """Process a single k-point and spin channel to find HOMO/LUMO."""
            spin_values, spin_occupations = kpoint_spin_data
            lumo_idx = quicksearch_first_value(
                spin_occupations, 0.0, tolerance=1e-6
            )

            return [
                spin_values[lumo_idx] if lumo_idx is not None and lumo_idx >= 0 else None,
                spin_values[lumo_idx + 1] if lumo_idx is not None and lumo_idx > 0 else None
            ]

        # Stack value and occupation arrays - shape: [level, kpoint, spin, 2]
        # Apply along level axis (axis=0) for each k-point and spin combination
        # Reshape to combine kpoint and spin dimensions for processing
        combined_data = np.stack([self.value, self.occupation.magnitude], axis=-1)
        n_levels, n_kpoints, n_spins, _ = combined_data.shape
        reshaped_data = combined_data.transpose(1, 2, 0, 3).reshape(n_kpoints * n_spins, n_levels, 2)
        results = np.apply_along_axis(process_kpoint_spin, axis=1, arr=reshaped_data)
        
        # Reshape back to [kpoint, spin, 2] then extract homo/lumo
        results = results.reshape(n_kpoints, n_spins, 2)
        self.highest_occupied = results[:, :, 0] * self.value.u
        self.lowest_unoccupied = results[:, :, 1] * self.value.u

    def pad_out(self) -> None:
        """
        Pad out the value and occupation arrays along the spin channel dimension.
        """
        spin_index = 2
        if np.array(self.value).shape[spin_index] == 1:  # TODO: add model_method spin_polarized
            self.value = inner_copy(self.value, 0)  # TODO: dynamically set repetition
        if np.array(self.occupation).shape[spin_index] == 1:  # TODO: add model_method spin_polarized
            self.occupation = inner_copy(self.occupation, 0)  # TODO: dynamically set repetition

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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.pad_out()
        self.resolve_homo_lumo()


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
