from typing import TYPE_CHECKING

import numpy as np
from nomad.metainfo import MEnum, Quantity, Reference
from nomad.metainfo.dataset import MDataset, Dataset
from nomad.datamodel.metainfo.model import ModelMethod

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

class Energy(MDataset):
    m_def = Dataset(
        type=np.float64,
        unit='joule',
        description="""A base section used to define basic quantities for the `TotalEnergy` property.""",
        default_variables=['Energy'],  # ? does this require variables of this shape
    )

    # ? origin_reference

    kind = Quantity(
        type=MEnum('kinetic', 'potential', 'total'),
    )

    method_reference = Quantity(
        type=Reference(ModelMethod),
        description="""
        Reference to a `ModelMethod` definition, according to which the energy was calculated.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        energy_sums = np.sum([var.data for var in self.variables if isinstance(var, Energy)], axis=0)
        if self.data is None or self.data == []:
            self.data = energy_sums
        elif not np.allclose(self.data, energy_sums):
            logger.warning(
                f'The sum of the energies in the variables is different from the total energy: {energy_sums} != {self.data}'
            )
