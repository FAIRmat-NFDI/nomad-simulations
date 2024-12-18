from typing import TYPE_CHECKING

import numpy as np
from nomad.units import ureg
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.datasets import DatasetTemplate, Energy
from ..variables import (
    SpinChannel,
    MomentumTransfer,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


class HomoLumoGap(ArchiveSection):  # ? class description
    values = DatasetTemplate(
        name='HomoLumoGap',
        mandatory_fields=[Energy],
        mandatory_variables=[SpinChannel],  # presence checked via annotations
        iri='http://fairmat-nfdi.eu/taxonomy/HomoLumoGap',
        description="""
        The energy difference between the highest occupied spin state
        and the lowest unoccupied spin state.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        self.m_all_validate()  # ensure constraints 
        if np.any((energies := self.get_variable(Energy).get_values()) < 0):  # ? failure handling
            logger.warning(f'Negative band gap detected: {energies.to('J').magnitude} J')


class ElectronicBandGap(HomoLumoGap):  # ! TODO: add optical band gap
    values = HomoLumoGap.values.m_copy()  # ? `m_copy` supported
    values.mandatory_variables.append(MomentumTransfer)
    values.iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap'

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
        if not self.get_variable(MomentumTransfer).get_values():  # getter
            if self.type == 'direct':
                self.variables.append(
                    MomentumTransfer(data=[2 * [3 * [0.0]]] * ureg.angstrom**-1)
                )
            elif self.type == 'indirect':
                logger.warning(
                    f'Indirect band gap without specifying any momentum transfer: {self.variables}'
                )
