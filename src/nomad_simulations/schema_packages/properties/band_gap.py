from typing import TYPE_CHECKING

import numpy as np
from nomad.units import ureg
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.dataset import MDataset
from nomad.datamodel.metainfo.physical_properties import PhysicalProperty
from nomad.datamodel.data import ArchiveSection
from ..variables import SpinChannel, MomentumTransfer

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


class ElectronicBandGap(MDataset, ArchiveSection):  # ? add optical band gap
    m_def = PhysicalProperty(
        type=np.float64,
        unit='joule',
        iri='http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap',
        description="""Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state.""",
        default_variables=['SpinChannel', 'MomentumTransfer'],
    )

    type = Quantity(
        type=MEnum('direct', 'indirect'),
        description="""
        Type categorization of the electronic band gap. This quantity is directly related with `momentum_transfer` as by
        definition, the electronic band gap is `'direct'` for zero momentum transfer (or if `momentum_transfer` is `None`) and `'indirect'`
        for finite momentum transfer.

        Note: in the case of finite `variables`, this quantity refers to all of the `value` in the array.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        # super().normalize(archive, logger)

        if np.any(self.data < 0):
            logger.warning(f'Negative band gap detected: {self.data} J')

        if [True for var in self.variables if isinstance(var, SpinChannel)]:
            logger.warning(
                f'Band gap without specifying any spin channel: {self.variables}'
            )

        if not [True for var in self.variables if isinstance(var, MomentumTransfer)]:
            if self.type == 'direct':
                self.variables.append(
                    MomentumTransfer(data=[2 * [3 * [0.0]]] * ureg.angstrom**-1)
                )
            elif self.type == 'indirect':
                logger.warning(
                    f'Indirect band gap without specifying any momentum transfer: {self.variables}'
                )

        # ? how to enforce a fixed ordering
