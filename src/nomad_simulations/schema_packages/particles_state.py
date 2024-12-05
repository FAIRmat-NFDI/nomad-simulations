import numbers
from typing import TYPE_CHECKING, Any, Optional, Union

import ase
import ase.geometry
import numpy as np
import pint

# from deprecated import deprecated
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.datamodel.metainfo.basesections import Entity
from nomad.metainfo import MEnum, Quantity, SubSection
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import State


# ? How generic (usable for any CG model) vs. Martini-specific do we want to be?
class ParticlesState(State):
    """
    A base section to define individual coarse-grained (CG) particle information.
    """

    # ? What do we want to qualify as type identifier? What safety checks do we need?
    particle_type = Quantity(
        type=str,
        description="""
        Symbol(s) describing the CG particle type. Currently, entire particle label is
        used for type definition.
        """,
    )

    mass = Quantity(
        type=np.float64,
        unit='kg',
        description="""
        Total mass of the particle.
        """,
    )

    charge = Quantity(
        type=np.float64,
        unit='coulomb',
        description="""
        Total charge of the particle.
        """,
    )

    charge = Quantity(
        type=np.float64,
        unit='coulomb',
        description="""
        Total charge of the particle.
        """,
    )

    # Other possible quantities
    #     diameter: float
    #         The diameter of each particle.
    #         Default: 1.0
    #     body: int
    #         The composite body associated with each particle. The value -1
    #         indicates no body.
    #         Default: -1
    #     moment_inertia: float
    #         The moment_inertia of each particle (I_xx, I_yy, I_zz).
    #         This inertia tensor is diagonal in the body frame of the particle.
    #         The default value is for point particles.
    #         Default: 0, 0, 0
    #     scaled_positions: list of scaled-positions #! for cell if relevant
    #         Like positions, but given in units of the unit cell.
    #         Can not be set at the same time as positions.
    #         Default: 0, 0, 0
    #     orientation: float
    #         The orientation of each particle. In scalar + vector notation,
    #         this is (r, a_x, a_y, a_z), where the quaternion is q = r + a_xi + a_yj + a_zk.
    #         A unit quaternion has the property: sqrt(r^2 + a_x^2 + a_y^2 + a_z^2) = 1.
    #         Default: 0, 0, 0, 0
    #     angmom: float #? for cell or here?
    #         The angular momentum of each particle as a quaternion.
    #         Default: 0, 0, 0, 0
    #     image: int #! advance PBC stuff would go in cell I guess
    #         The number of times each particle has wrapped around the box (i_x, i_y, i_z).
    #         Default: 0, 0, 0

    # ? What is the purpose exactly of this function? Example?
    def resolve_particle_type(self, logger: 'BoundLogger') -> Optional[str]:
        """
        Checks if any value is passed as particle label. Converts to string to be used as
        type identifier for the CG particle.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[str]): The resolved `particle type`.
        """
        if self.particle_type is not None and self.particle_type.isascii():
            try:
                return str(self.particle_type)
            except TypeError:
                logger.error('The parsed `particle type` can not be read.')
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Get particle_type as string, if possible.
        if not isinstance(self.particle_type, str):
            self.particle_type = self.resolve_particle_type(logger=logger)
