from typing import TYPE_CHECKING, Optional

import numpy as np
from nomad.metainfo import MEnum, Quantity

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.data_types import positive_float
from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.utils import log


class ElectronicBandGap(PhysicalProperty):
    """
    Energy difference between the highest occupied electronic state and the lowest unoccupied electronic state.
    """

    iri = 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandGap'

    type = Quantity(
        type=MEnum('direct', 'indirect'),
        description="""
        Type categorization of the electronic band gap. This quantity is directly related with `momentum_transfer` as by
        definition, the electronic band gap is `'direct'` for zero momentum transfer (or if `momentum_transfer` is `None`) and `'indirect'`
        for finite momentum transfer.
        """,
    )

    momentum_transfer = Quantity(
        type=np.float64,
        shape=[2, 3],
        description="""
        If the electronic band gap is `'indirect'`, the reciprocal momentum transfer for which the band gap is defined
        in units of the `reciprocal_lattice_vectors`. The initial and final momentum 3D vectors are given in the first
        and second element. Example, the momentum transfer in bulk Si2 happens between the Γ and the (approximately)
        X points in the Brillouin zone; thus:
            `momentum_transfer = [[0, 0, 0], [0.5, 0.5, 0]]`.

        Note: this quantity only refers to scalar `value`, not to arrays of `value`.
        """,
    )

    spin_channel = Quantity(
        type=np.int32,
        description="""
        Spin channel of the corresponding electronic band gap. It can take values of 0 or 1.
        """,
    )

    value = Quantity(
        type=positive_float(),
        unit='joule',
        description="""
        The value of the electronic band gap. This value must be positive.
        """,
    )

    @log
    def resolve_type(self) -> str | None:
        """
        Resolves the `type` of the electronic band gap based on the stored `momentum_transfer` values.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[str]): The resolved `type` of the electronic band gap.
        """
        logger = self.resolve_type.__annotations__['logger']
        mtr = self.momentum_transfer if self.momentum_transfer is not None else []

        # Check if the `momentum_transfer` is [], and return the type and a warning in the log for `indirect` band gaps
        if len(mtr) == 0:
            if self.type == 'indirect':
                logger.warning(
                    'The `momentum_transfer` is not stored for an `indirect` band gap.'
                )
            return self.type

        # Check if the `momentum_transfer` has at least two elements, and return None if it does not
        if len(mtr) == 1:
            logger.warning(
                'The `momentum_transfer` should have at least two elements so that the difference can be calculated and the type of electronic band gap can be resolved.'
            )
            return None

        # Resolve `type` from the difference between the initial and final momentum transfer
        momentum_difference = np.diff(mtr, axis=0)
        if (np.isclose(momentum_difference, np.zeros(3))).all():
            return 'direct'
        else:
            return 'indirect'

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve the `type` of the electronic band gap from `momentum_transfer`, ONLY for scalar `value`
        if self.value is not None:
            self.type = self.resolve_type(logger=logger)
