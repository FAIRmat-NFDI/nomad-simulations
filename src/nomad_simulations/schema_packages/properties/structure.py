from typing import TYPE_CHECKING

import numpy as np
from nomad.metainfo import Quantity

if TYPE_CHECKING:
    pass

from nomad_simulations.schema_packages.physical_property import PhysicalProperty


class RadiusOfGyration(PhysicalProperty):
    """
    Radius of gyration (Rg).
    """

    value = Quantity(
        type=np.float64,
        shape=[],
        unit='m',
        description="""
        Value of Rg.
        """,
    )
