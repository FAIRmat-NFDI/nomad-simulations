import numpy as np
from nomad.metainfo import Quantity, SubSection, SectionProxy
from nomad_simulations.schema_packages.physical_property import PhysicalProperty

##################
# Abstract classes
##################


class TotalForce(PhysicalProperty):
    """
    Abstract class used to define a common `value` quantity with the appropriate units
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

    contributions = SubSection(
        sub_section=SectionProxy('TotalForce'),
        repeats=True,
        description="""
        The contributions to the total force. Each contribution is a specific force
        component, such as the force from a specific potential or interaction.
        """,
    )
