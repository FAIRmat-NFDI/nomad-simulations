from typing import TYPE_CHECKING

import numpy as np
from nomad.units import ureg
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.physical_properties import MaterialProperty, Energy
from ..variables import (
    SpinChannel,
    MomentumTransfer,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


class ElectronicBandGap(ArchiveSection):  # ! TODO: add optical band gap
    values = MaterialProperty(
        name='BandGap',
        fields=[Energy],
        variables=[SpinChannel, MomentumTransfer],  # presence checked via annotations
        iri='http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap',
        description="""Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state.""",  # ? necessity
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
        if np.any(self.values.fields < 0):  # ? check for Energy
            logger.warning(f'Negative band gap detected: {self.values.fields} J')

        if not self.variables[1]:  # ! replace with native getter
            if self.type == 'direct':
                self.variables.append(
                    MomentumTransfer(data=[2 * [3 * [0.0]]] * ureg.angstrom**-1)
                )
            elif self.type == 'indirect':
                logger.warning(
                    f'Indirect band gap without specifying any momentum transfer: {self.variables}'
                )
