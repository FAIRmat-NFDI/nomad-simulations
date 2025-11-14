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
