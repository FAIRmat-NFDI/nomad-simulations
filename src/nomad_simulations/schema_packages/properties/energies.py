import numpy as np
from nomad.metainfo import Quantity, SectionProxy, SubSection

from nomad_simulations.schema_packages.physical_property import PhysicalProperty

##################
# Abstract classes
##################


class BaseEnergy(PhysicalProperty):
    """
    Abstract class used to define a common `value` quantity with the appropriate units
    for different types of energies, which avoids repeating the definitions for each
    energy class.
    """

    value = Quantity(
        type=np.float64,
        unit='joule',
        description="""
        """,
    )


####################################
# List of specific energy properties
####################################


#! The only issue with this structure is that total energy will never be a sum of its contributions,
#! since kinetic energy lives separately, but I think maybe this is ok?
class TotalEnergy(BaseEnergy):
    """
    The converged total energy of one system configuration.

    Individual energetic components belong inside this section through its
    `contributions` subsections. The listed contributions do not have to be
    exhaustive, so the total energy is not necessarily equal to their sum.
    """

    # ? add a generic contributions quantity to PhysicalProperty
    contributions = SubSection(sub_section=SectionProxy('BaseEnergy'), repeats=True)


# ? Separate quantities for nuclear and electronic KEs?
class KineticEnergy(BaseEnergy):
    """
    Physical property section describing the kinetic energy of a (sub)system.
    """


class PotentialEnergy(BaseEnergy):
    """
    Physical property section describing the potential energy of a (sub)system.
    """
