from typing import TYPE_CHECKING, Optional

from enum import Enum
import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from nomadmetainfo.physical_properties import (
    PhysicalProperty,
    MaterialProperty,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.numerical_settings import (
    KLinePath as KLinePathSettings,
)
from nomad_simulations.schema_packages.numerical_settings import (
    KMesh as KMeshSettings,
)


class MaterialPropertyAttributes(Enum):
    fields = 'fields'
    variables = 'variables'


def fetch_instance(
    prop: MaterialProperty,
    target: PhysicalProperty,
    attribute: MaterialPropertyAttributes = MaterialPropertyAttributes.fields,
) -> np.ndarray[PhysicalProperty]:
    """
    Fetches instances of a specified physical property from a material property based on a given attribute.

    Args:
        prop (MaterialProperty): The material property from which to fetch instances.
        target (PhysicalProperty): The type of physical property to fetch.
        attribute (MaterialPropertyAttributes): The attribute of the material property to check.

    Returns:
        np.ndarray[PhysicalProperty]: An array of instances of the specified physical property.

    Raises:
        ValueError: If the provided attribute is not a valid MaterialProperty attribute.
    """
    if not isinstance(attribute, MaterialPropertyAttributes):
        raise ValueError(
            f'Attribute {attribute} is not a valid MaterialProperty attribute.'
        )
    return np.where(lambda x: isinstance(x, target), getattr(prop, attribute), [])


SpinChannel = PhysicalProperty(
    name='SpinChannel',
    type=MEnum('alpha', 'beta', 'both'),
    # ! iri
)


KMesh = PhysicalProperty(
    type=np.float64,  # ? KMeshSettings.points,
    shape=[3],
    unit='1/m',
    description="""
        K-point mesh over which the physical property is calculated. This is used to define `ElectronicEigenvalues(PhysicalProperty)` and
        other k-space properties. The `points` are obtained from a reference to the `NumericalSettings` section, `KMesh(NumericalSettings)`.
        """,
    # ! iri
)


MomentumTransfer = PhysicalProperty(
    type=np.float64,
    shape=[2, 3],
    unit='1/meter',
    description="""
            The change in momentum for any (quasi-)particle, e.g. electron, hole,
            traversing the band gap.

            For example, the momentum transfer in bulk Si happens
            between the Γ and X points in the Brillouin zone; thus:
                `momentum_transfer = [[0, 0, 0], [0.5, 0.5, 0]]`.
            """,
    # ! iri
)


class Variables(ArchiveSection):
    """
    Variables over which the physical property varies, and they are defined as grid points, i.e., discretized
    values by `n_points` and `points`. These are used to calculate the `shape` of the physical property.
    """

    name = Quantity(
        type=str,
        default='Custom',
        description="""
        Name of the variable.
        """,
    )

    n_points = Quantity(
        type=int,
        description="""
        Number of points in which the variable is discretized.
        """,
    )

    points = Quantity(
        type=np.float64,
        # shape=['n_points'],  # ! if defined, this breaks using `points` as refs (e.g., `KMesh.points`)
        description="""
        Points in which the variable is discretized. It might be overwritten with specific units.
        """,
    )

    # ? Do we need to add `points_error`?

    def get_n_points(self, logger: 'BoundLogger') -> Optional[int]:
        """
        Get the number of grid points from the `points` list. If `n_points` is previously defined
        and does not coincide with the length of `points`, a warning is issued and this function re-assigns `n_points`
        as the length of `points`.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[int]): The number of points.
        """
        if self.points is not None and len(self.points) > 0:
            if self.n_points != len(self.points) and self.n_points is not None:
                logger.warning(
                    f'The stored `n_points`, {self.n_points}, does not coincide with the length of `points`, '
                    f'{len(self.points)}. We will re-assign `n_points` as the length of `points`.'
                )
            return len(self.points)
        return self.n_points

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Setting `n_points` if these are not defined
        self.n_points = self.get_n_points(logger)


class Temperature(Variables):
    """ """

    points = Quantity(
        type=np.float64,
        unit='kelvin',
        shape=['n_points'],
        description="""
        Points in which the temperature is discretized.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


# ! This needs to be fixed as it gives errors when running normalizers with conflicting names (ask Area D)
class Energy2(Variables):
    """ """

    points = Quantity(
        type=np.float64,
        unit='joule',
        shape=['n_points'],
        description="""
        Points in which the energy is discretized.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class WignerSeitz(Variables):
    """
    Wigner-Seitz points in which the real space is discretized. This variable is used to define `HoppingMatrix(PhysicalProperty)` and
    other inter-cell properties. See, e.g., https://en.wikipedia.org/wiki/Wigner–Seitz_cell.
    """

    points = Quantity(
        type=np.float64,
        shape=['n_points', 3],
        description="""
        Wigner-Seitz points with respect to the origin cell, (0, 0, 0). These are 3D arrays stored in fractional coordinates.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class Frequency(Variables):
    """ """

    points = Quantity(
        type=np.float64,
        unit='joule',
        shape=['n_points'],
        description="""
        Points in which the frequency is discretized, in joules.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class MatsubaraFrequency(Variables):
    """ """

    points = Quantity(
        type=np.complex128,
        unit='joule',
        shape=['n_points'],
        description="""
        Points in which the imaginary or Matsubara frequency is discretized, in joules.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class Time(Variables):
    """ """

    points = Quantity(
        type=np.float64,
        unit='second',
        shape=['n_points'],
        description="""
        Points in which the time is discretized, in seconds.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class ImaginaryTime(Variables):
    """ """

    points = Quantity(
        type=np.complex128,
        unit='second',
        shape=['n_points'],
        description="""
        Points in which the imaginary time is discretized, in seconds.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class KLinePath(Variables):
    """ """

    points = Quantity(
        type=KLinePathSettings.points,
        description="""
        Reference to the `KLinePath.points` in which the physical property is calculated. These are 3D arrays stored in fractional coordinates.
        """,
    )

    def __init__(
        self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs
    ) -> None:
        super().__init__(m_def, m_context, **kwargs)
        self.name = self.m_def.name

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
