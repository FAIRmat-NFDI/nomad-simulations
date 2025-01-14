from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.datamodel.metainfo import ArchiveSection
from ..variables import VirialTensor, Hessian


def is_square(shape: tuple[int, int]) -> bool:
    return shape[0] == shape[1]

class ModelVirialTensorSection(ArchiveSection):  # ? set via decorator
    virial_tensor = VirialTensor()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        if not is_square(self.virial_tensor.shape):
            logger.error('Virial tensor is not square', shape=self.virial_tensor.shape)

class ModelHessianSection(ArchiveSection):
    hessian = Hessian()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        if not is_square(self.hessian.shape):
            logger.error('Hessian matrix is not square', shape=self.hessian.shape)
