from typing import TYPE_CHECKING, Optional

import numpy as np
import pint
from nomad.metainfo import MEnum, Quantity

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class ElectronicBandGap(PhysicalProperty):
    """
    Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state.
    """

    # ! implement `iri` and `rank` as part of `m_def = Section()`

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap'

    type = Quantity(
        type=MEnum('direct', 'indirect'),
        shape=['*'],
        description="""
        Type categorization of the electronic band gap. This quantity is directly related with `momentum_transfer` as by
        definition, the electronic band gap is `'direct'` for zero momentum transfer (or if `momentum_transfer` is `None`) and `'indirect'`
        for finite momentum transfer.

        Note: in the case of finite `variables`, this quantity refers to all of the `value` in the array.
        """,
    )

    momentum_transfer = Quantity(
        type=np.float64,
        shape=['*', 2, 3],
        description="""
        If the electronic band gap is `'indirect'`, the reciprocal momentum transfer for which the band gap is defined
        in units of the `reciprocal_lattice_vectors`. The initial and final momentum 3D vectors are given in the first
        and second element. Example, the momentum transfer in bulk Si2 happens between the Γ and the (approximately)
        X points in the Brillouin zone; thus:
            `momentum_transfer = [[[0, 0, 0], [0.5, 0.5, 0]]]`.
        """,
    )

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic band gap. It can take values of 0 or 1.
        """,
    )

    _base_value = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        The value of the electronic band gap. This value has to be positive, otherwise it will
        prop an error and be set to None by the `normalize()` function.
        """,
    )

    def momentum_to_type(self, mtr, logger: 'BoundLogger') -> Optional[str]:
        """
        Resolves the `type` of the electronic band gap based on the stored `momentum_transfer` values.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[str]): The resolved `type` of the electronic band gap.
        """
        
        # Resolve `type` from the difference between the initial and final momentum transfer
        momentum_difference = np.diff(mtr, axis=0)
        if (np.isclose(momentum_difference, np.zeros(3))).all():
            return 'direct'
        else:
            return 'indirect'

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.value is not None and np.any(self.value < 0.):
            logger.warning('The electronic band gap cannot be defined negative.')
            # ? What about deleting the class if `value` is None?

        if self.momentum_transfer:
            self.type = self.momentum_to_type(self.momentum_transfer, logger)
