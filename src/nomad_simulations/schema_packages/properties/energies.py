from typing import TYPE_CHECKING
import numpy as np

from ..physical_property import PhysicalPropertyDecomposition
from ..variables import Energy, EnergyType, MethodReference

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

EnergyTemplateGenerator = PhysicalPropertyDecomposition(
    Energy,
    reference_type=MethodReference,
)


class ModelEnergySection('ArchiveSection'):
    energy = EnergyTemplateGenerator()()  # ? suggest energy_origin or kind

    type = EnergyType()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # check that the contributions do not outgrow the total energy
        for field in self.energy.fields:
            if (total_energy := field[0]) < (energy_contributions := np.sum(field[1])):
                logger.warning(
                    f'The contributions outweigh the total energy',
                    energy_contributions,
                    total_energy,
                )
