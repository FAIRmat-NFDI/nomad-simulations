from typing import TYPE_CHECKING

import numpy as np
from nomad.units import ureg
from nomad.datamodel.data import ArchiveSection
from ..variables import (
    KMomentumTransfer,
    ElectronicBandGap,
    BandGapType,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


class ElectronicBandGapSection(ArchiveSection):  # ! TODO: add optical band gap
    band_gap = ElectronicBandGap()

    band_gap_type = BandGapType()

    def type_to_gap(self, logger: 'BoundLogger'):
        bg, bt = self.band_gap.get_fields(), self.band_gap_type.get_fields()
        if bg is not None:
            return
        
        if self.type == 'direct':
            self.variables.append(
                KMomentumTransfer(data=[2 * [3 * [0.0]]] * ureg.angstrom**-1)
            )
        elif self.type == 'indirect':
            logger.warning(
                f'Indirect band gap without specifying any momentum transfer: {self.variables}'
            )

    def gap_to_type(self):
        if self.band_gap_type.get_fields() is not None:
            return
        if self.band_gap.get_variables(KMomentumTransfer):
            self.band_gap_type = ...
        else:
            self.band_gap_type = 'unknown'


    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.type_to_gap(logger)
        self.gap_to_type()
