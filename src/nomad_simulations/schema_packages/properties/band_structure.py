from typing import TYPE_CHECKING, Optional

import numpy as np
import pint
from nomad.config import config
from nomad.metainfo import Quantity, SubSection

from nomad_simulations.schema_packages.numerical_settings import KMesh

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import AtomsState, OrbitalsState
from nomad_simulations.schema_packages.data_types import unit_float
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.physical_property import PhysicalProperty

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class BaseElectronicEigenvalues(PhysicalProperty):
    """
    A base section used to define basic quantities for the `ElectronicEigenvalues`  and `ElectronicBandStructure` properties.
    """

    iri = ''

    n_bands = Quantity(
        type=np.int32,
        description="""
        Number of bands / eigenvalues.
        """,
    )  # TODO: remove

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
        type=unit_float(),
        shape=['*'],
        description="""
        Occupation of the electronic eigenvalues. 
        """,
    )  # restructure spin for plotting?

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


class ElectronicBandStructure(ElectronicEigenvalues):
    """
    Accessible energies by the charges (electrons and holes) in the reciprocal space.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'

    k_path = SubSection(sub_section=KMesh.m_def)

    def resolve_reciprocal_cell(self) -> Optional[pint.Quantity]:
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
        self.reciprocal_cell = self.resolve_reciprocal_cell()


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
