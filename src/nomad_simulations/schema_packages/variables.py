from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import Quantity

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.numerical_settings import (
    KLinePath as KLinePathSettings,
)
from nomad_simulations.schema_packages.numerical_settings import KMesh as KMeshSettings
from nomad_simulations.schema_packages.utils import log


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
    @log
    def get_n_points(self) -> int | None:
        """
        Get the number of grid points from the `points` list. If `n_points` is previously defined
        and does not coincide with the length of `points`, a warning is issued and this function re-assigns `n_points`
        as the length of `points`.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[int]): The number of points.
        """
        logger = self.get_n_points.__annotations__['logger']
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
        self.n_points = self.get_n_points(logger=logger)

        if self.m_def.name is not None:
            self.name = self.m_def.name


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


class KMesh(Variables):
    """
    K-point mesh over which the physical property is calculated, expressed as a reference into the
    `KMesh(NumericalSettings)` section. Superseded by `KPoints` for new properties, which stores the
    evaluated points directly on the property; retained for its existing consumers
    (`BaseGreensFunction.k_mesh`, `Permittivity.q_mesh`).
    """

    points = Quantity(
        type=KMeshSettings.points,
        description="""
        Reference to the `KMesh.points` over which the physical property is calculated. These are 3D arrays stored in fractional coordinates.
        """,
    )


class KPoints(Variables):
    """
    Reciprocal-space points at which a physical property is evaluated, stored directly as
    fractional coordinates. The points form an ordered list: their sequence is meaningful and
    duplicate points are allowed (e.g. a closed path visiting the same high-symmetry point twice).
    The optional `weights` carry the Brillouin-zone integration measure of a (possibly irreducible)
    mesh sampling; they remain unset when the points do not sample the full zone, as for a line
    path. The corresponding generation settings, if any, are described independently under
    `KSpace(NumericalSettings)`.
    """

    points = Quantity(
        type=np.float64,
        shape=['n_points', 3],
        description="""
        K-points at which the physical property is evaluated, stored in fractional coordinates.
        """,
    )

    weights = Quantity(
        type=np.float64,
        shape=['n_points'],
        description="""
        Brillouin-zone integration weight of each point, normalized to sum to 1. Set when `points`
        form a (possibly symmetry-reduced) sampling of the full zone; unset for line paths.
        """,
    )


class KLinePath(KPoints):
    """
    K-points sampled along a high-symmetry line path. The path is structure on top of the ordered
    point list inherited from `KPoints`: consecutive high-symmetry points delimit segments (e.g.
    Γ→X, X→M), each containing multiple sampling points. `high_symmetry_labels` and
    `high_symmetry_indices` locate the delimiting points within `points`, which suffices to build
    a cumulative-distance plot axis with labeled ticks. The inherited `weights` remain unset, as a
    path carries no Brillouin-zone integration measure.
    """

    high_symmetry_labels = Quantity(
        type=str,
        shape=['*'],
        description="""
        Labels of the high-symmetry points delimiting the path segments, in traversal order,
        e.g. `['Γ', 'X', 'M', 'Γ']`. Each label corresponds to the entry of
        `high_symmetry_indices` at the same position.
        """,
    )

    high_symmetry_indices = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        Index into `points` of each high-symmetry point named in `high_symmetry_labels`.
        Consecutive indices delimit the path segments.
        """,
    )

    settings_ref = Quantity(
        type=KLinePathSettings,
        description="""
        Reference to the abstract path definition in the `KLinePath(NumericalSettings)` section
        (high-symmetry path names and values, line density). Provenance only: the sampled
        coordinates are stored directly in `points`.
        """,
    )
