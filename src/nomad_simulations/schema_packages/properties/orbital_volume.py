from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.hdf5 import HDF5Dataset
from nomad.datamodel.metainfo.annotations import H5WebAnnotation
from nomad.metainfo import Quantity, Reference, Section, SectionProxy

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


class OrbitalVolume(ArchiveSection):
    m_def = Section(
        a_h5web=H5WebAnnotation(signal='field'),
        description="""
        Real-space orbital volume data for a single molecular orbital.
        """,
    )

    orbital_index = Quantity(type=np.int32)
    label = Quantity(type=str)
    energy = Quantity(type=np.float64, unit='joule')
    occupation = Quantity(type=np.float64)
    spin = Quantity(type=str)
    symmetry = Quantity(type=str)
    source_file = Quantity(type=str)

    field = Quantity(
        type=HDF5Dataset,
        shape=[],
        description="""
        Signed scalar field sampled on a regular 3D grid for a single molecular orbital.
        """,
    )

    grid_origin = Quantity(type=np.float64, shape=[3], unit='meter')
    grid_vectors = Quantity(type=np.float64, shape=[3, 3], unit='meter')
    grid_shape = Quantity(type=np.int32, shape=[3])
    default_isovalue = Quantity(type=np.float64)

    model_system_ref = Quantity(
        type=Reference(
            SectionProxy('nomad_simulations.schema_packages.model_system.ModelSystem')
        )
    )
    molecular_orbitals_ref = Quantity(
        type=Reference(
            SectionProxy(
                'nomad_simulations.schema_packages.properties.molecular_orbitals.MolecularOrbitals'
            )
        )
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.grid_shape is None and hasattr(self.field, 'shape'):
            self.grid_shape = np.asarray(self.field.shape, dtype=np.int32)
