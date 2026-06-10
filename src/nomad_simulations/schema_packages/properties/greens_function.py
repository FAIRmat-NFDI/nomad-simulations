from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.hdf5 import HDF5Dataset
from nomad.metainfo import MEnum, Quantity, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.context import Context
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import AtomsState, ElectronicState
from nomad_simulations.schema_packages.data_types import unit_float
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.variables import (
    Frequency,
    ImaginaryTime,
    KMesh,
    MatsubaraFrequency,
    Time,
    WignerSeitz,
)


class BaseGreensFunction(PhysicalProperty):
    """
    A base class used to define shared commonalities between Green's function-related properties. This is the case for `ElectronicGreensFunction`,
    `ElectronicSelfEnergy`, `HybridizationFunction` in DMFT simulations.

    These physical properties are matrices matrix represented in different spaces. These spaces can be:
    `WignerSeitz` (real space), `KMesh`, `MatsubaraFrequency`, `Frequency`, `Time`, or `ImaginaryTime`.
    For example, G(k, ω) will have corresponds to `k_mesh` and `real_frequency` being set.

    The `entity_ref` field points to an `ElectronicState` describing the correlated orbitals. To access the
    parent AtomsState, use `entity_ref.get_parent_entity()`. This follows the ElectronicState gateway pattern.

    Further information in M. Wallerberger et al., Comput. Phys. Commun. 235, 2 (2019).
    """

    n_atoms = Quantity(
        type=np.int32,
        description="""
        Number of atoms involved in the correlations effect and used for the matrix representation of the property.
        Can be derived from entity_ref if needed.
        """,
    )

    entity_ref = Quantity(
        type=ElectronicState,
        description="""
        Reference to the `ElectronicState` section describing the correlated orbitals for which the
        Green's function properties are calculated. The parent AtomsState can be accessed via
        `entity_ref.get_parent_entity()`.
        """,
    )

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic property. It can take values of 0 and 1.
        """,
    )

    local_model_type = Quantity(
        type=MEnum('impurity', 'lattice'),
        description="""
        Type of Green's function calculated from the mapping of the local Hubbard-Kanamori model
        into the Anderson impurity model.

        The `impurity` Green's function describe the electronic correlations for the impurity, and it
        is a local function. The `lattice` Green's function includes the coupling to the lattice
        and hence it is a non-local function. In DMFT, the `lattice` term is approximated to be the
        `impurity` one, so that these simulations are converged if both types of the local
        part of the `lattice` Green's function coincides with the `impurity` Green's function.
        """,
    )

    space_id = Quantity(
        type=MEnum(
            'r',
            'rt',
            'rw',
            'rit',
            'riw',
            'k',
            'kt',
            'kw',
            'kit',
            'kiw',
            't',
            'it',
            'w',
            'iw',
        ),
        description="""
        String used to identify the space in which the Green's function property is represented. The spaces are:

        | `space_id` | variable type |
        | ------ | ------ |
        | 'r' | WignerSeitz |
        | 'rt' | WignerSeitz + Time |
        | 'rw' | WignerSeitz + Frequency |
        | 'rit' | WignerSeitz + ImaginaryTime |
        | 'riw' | WignerSeitz + MatsubaraFrequency |
        | 'k' | KMesh |
        | 'kt' | KMesh + Time |
        | 'kw' | KMesh + Frequency |
        | 'kit' | KMesh + ImaginaryTime |
        | 'kiw' | KMesh + MatsubaraFrequency |
        | 't' | Time |
        | 'it' | Frequency |
        | 'w' | ImaginaryTime |
        | 'iw' | MatsubaraFrequency |
        """,
    )

    wigner_seitz = SubSection(sub_section=WignerSeitz.m_def)

    k_mesh = SubSection(sub_section=KMesh.m_def)

    matsubara_frequency = SubSection(sub_section=MatsubaraFrequency.m_def)

    real_frequency = SubSection(sub_section=Frequency.m_def)

    time = SubSection(sub_section=Time.m_def)

    imaginary_time = SubSection(sub_section=ImaginaryTime.m_def)

    def resolve_space_id(self) -> str:
        """
        Resolves the `space_id` of the Green's function property.
        """

        space_tag = ''
        if self.wigner_seitz is not None:
            space_tag += 'r'
        elif self.k_mesh is not None:
            space_tag += 'k'

        time_tag = ''
        if self.time is not None:
            time_tag += 't'
        elif self.imaginary_time is not None:
            time_tag += 'it'
        elif self.real_frequency is not None:
            time_tag += 'w'
        elif self.matsubara_frequency is not None:
            time_tag += 'iw'

        if space_id := space_tag + time_tag:
            return space_id
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        space_id = self.resolve_space_id()
        if self.space_id is not None and self.space_id != space_id:
            logger.warning(
                f'The stored `space_id`, {self.space_id}, does not coincide with the resolved one, {space_id}. We will update it.'
            )
        self.space_id = space_id


class ElectronicGreensFunction(BaseGreensFunction):
    """
    Charge-charge correlation functions.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicGreensFunction'

    value = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='1/joule',
        description="""
        Value of the electronic Green's function matrix stored as an HDF5 dataset.
        The conventional dataset layout is [n_kpoints, n_frequencies, n_orbitals, n_orbitals]
        for k- and frequency-resolved Green's functions, but the actual dimensions depend on
        the represented spaces set via the `space_id` field.
        """,
    )


class ElectronicSelfEnergy(BaseGreensFunction):
    """
    Corrections to the energy of an electron due to its interactions with its environment.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicSelfEnergy'

    value = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='joule',
        description="""
        Value of the electronic self-energy matrix stored as an HDF5 dataset.
        The conventional dataset layout is [n_kpoints, n_frequencies, n_orbitals, n_orbitals]
        for k- and frequency-resolved self-energies, but the actual dimensions depend on
        the represented spaces set via the `space_id` field.
        """,
    )


class HybridizationFunction(BaseGreensFunction):
    """
    Dynamical hopping of the electrons in a lattice in and out of the reservoir or bath.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/HybridizationFunction'

    value = Quantity(
        type=HDF5Dataset,
        shape=[],
        unit='joule',
        description="""
        Value of the electronic hybridization function stored as an HDF5 dataset.
        The conventional dataset layout is [n_kpoints, n_frequencies, n_orbitals, n_orbitals]
        for k- and frequency-resolved hybridization functions, but the actual dimensions depend on
        the represented spaces set via the `space_id` field.
        """,
    )


class QuasiparticleWeight(PhysicalProperty):
    """
    Renormalization of the electronic mass due to the interactions with the environment. Within the Fermi liquid
    theory of solids, this is calculated as:

        Z = 1 - ∂Σ/∂ω|ω=0

    where Σ is the `ElectronicSelfEnergy`. The quasi-particle weight is a measure of the strength of the
    electron-electron interactions and takes values between 0 and 1, with Z = 1 representing a non-correlated
    system, and Z = 0 the Mott state.

    The `entity_ref` field points to an `ElectronicState` describing the correlated orbitals. To access the
    parent AtomsState, use `entity_ref.get_parent_entity()`. This follows the ElectronicState gateway pattern.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/HybridizationFunction'

    system_correlation_strengths = Quantity(
        type=MEnum(
            'non-correlated metal',
            'strongly-correlated metal',
            'OSMI',
            'Mott insulator',
        ),
        description="""
        String used to identify the type of system based on the strength of the electron-electron interactions.

        | `type` | Description |
        | ------ | ------ |
        | 'non-correlated metal' | All `value` are above 0.7. Renormalization effects are negligible. |
        | 'strongly-correlated metal' | All `value` are below 0.4 and above 0. Renormalization effects are important. |
        | 'OSMI' | Orbital-selective Mott insulator: some orbitals have a zero `value` while others a finite one. |
        | 'Mott insulator' | All `value` are 0.0. Mott insulator state. |
        """,
    )

    n_atoms = Quantity(
        type=np.int32,
        description="""
        Number of atoms involved in the correlations effect and used for the matrix representation of the quasiparticle weight.
        Can be derived from entity_ref if needed.
        """,
    )

    n_correlated_orbitals = Quantity(
        type=np.int32,
        description="""
        Number of orbitals involved in the correlations effect and used for the matrix representation of the quasiparticle weight.
        """,
    )

    entity_ref = Quantity(
        type=ElectronicState,
        description="""
        Reference to the `ElectronicState` section describing the correlated orbitals for which the
        quasiparticle weight is calculated. The parent AtomsState can be accessed via
        `entity_ref.get_parent_entity()`.
        """,
    )

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic property. It can take values of 0 and 1.
        """,
    )

    value = Quantity(
        type=unit_float(),
        shape=['*'],
        description="""
        Value of the quasi-particle weight matrices. Must be between 0 and 1.
        """,
    )

    def resolve_system_correlation_strengths(self) -> str:
        """
        Resolves the `system_correlation_strengths` of the quasiparticle weight based on the stored `value` values.

        Returns:
            str: The resolved `system_correlation_strengths` of the quasiparticle weight.
        """
        value = np.array(self.value)
        if np.all(value > 0.7):
            return 'non-correlated metal'
        elif np.all((value < 0.4) & (value > 0)):
            return 'strongly-correlated metal'
        elif np.any(value == 0) and np.any(value > 0):
            return 'OSMI'
        elif np.all(value < 1e-2):
            return 'Mott insulator'
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.value is not None:
            system_correlation_strengths = self.resolve_system_correlation_strengths()
            if (
                self.system_correlation_strengths is not None
                and self.system_correlation_strengths != system_correlation_strengths
            ):
                logger.warning(
                    f'The stored `system_correlation_strengths`, {self.system_correlation_strengths}, does not coincide with the resolved one, {system_correlation_strengths}. We will update it.'
                )
            self.system_correlation_strengths = system_correlation_strengths
