import numpy as np
from nomad.metainfo import Quantity, SectionProxy, SubSection

from nomad_simulations.schema_packages.physical_property import PhysicalProperty

##################
# Abstract classes
##################


class BaseForce(PhysicalProperty):
    """
    Base class used to define a common `value` quantity with the appropriate units
    for different types of forces, which avoids repeating the definitions for each
    force class.
    """

    value = Quantity(
        type=np.dtype(np.float64),
        shape=['*', '*'],
        unit='newton',
        description="""
        """,
    )


class TotalForce(BaseForce):
    """
    The total force of a system. `contributions` specify individual
    contributions to the `TotalForce`.
    """

    contributions = SubSection(sub_section=SectionProxy('BaseForce'), repeats=True)
