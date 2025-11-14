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
    AtomsState,
    ElectronicState,
)
from nomad_simulations.schema_packages.numerical_settings import KSpace
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.band_gap import ElectronicBandGap
from nomad_simulations.schema_packages.properties.electronic_eigenvalues import (
    ElectronicEigenvalues,
)
from nomad_simulations.schema_packages.properties.fermi_surface import FermiSurface
from nomad_simulations.schema_packages.utils import get_sibling_section, log

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class ElectronicBandStructure(ElectronicEigenvalues):
    """
    Accessible energies by the charges (electrons and holes) in the reciprocal space.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'

    k_path = SubSection(sub_section=KLinePath.m_def)


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
