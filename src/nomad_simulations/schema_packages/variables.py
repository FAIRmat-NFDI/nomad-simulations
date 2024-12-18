from typing import TYPE_CHECKING, Optional

import numpy as np
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.datasets import (
    ValuesTemplate,
    DatasetTemplate,
    Energy,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger


KPoint = ValuesTemplate(
    type=np.float64,  # ? KMeshSettings.points,
    shape=['*'],
    unit='1/m',
    description="""
        K-point mesh over which the physical property is calculated.
        """,
    # ! iri
)


KMomentumTransfer = ValuesTemplate(
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


SpinChannel = ValuesTemplate(
    name='SpinChannel',
    type=MEnum('alpha', 'beta', 'both'),
    # ! iri
)


# ? SpinState


FermiLevel = DatasetTemplate(
    name='FermiLevel',
    mandatory_fields=[Energy],
    # iri
)


FermiSurface = DatasetTemplate(
    name='FermiSurface',
    mandatory_fields=[Energy],
    mandatory_variables=[KPoint],  # ? band indices
    description="""
    The Fermi surface is the surface in the reciprocal space that separates the occupied states from the unoccupied states at absolute zero temperature.
    """,
    # ! iri
)


ElectronicStateOccupation = ValuesTemplate(
    name='ElectronicStateOccupation',
    type=np.float64,  # [0,1] or [0,2]
    shape=['*'],
    description="""
    Occupation of an orbital or spin channel. This is a number defined between 0 and 1 for
    spin-polarized systems, and between 0 and 2 for non-spin-polarized systems. This property is
    important when studying if an orbital or spin channel are fully occupied, at half-filling, or
    fully emptied, which have an effect on the electron-electron interaction effects.
    """,
    # ! iri
)


ElectronicStateDensity = ValuesTemplate(
    name='ElectronicStateDensity',
    type=np.float64,
    shape=['*'],
    description="""
    Density of electronic states. This property is important when studying the electronic structure
    of a material, and it is used to calculate the density of states (DOS).
    """,
    # ! iri
)


HomoLumoGap = DatasetTemplate(
    name='HomoLumoGap',
    mandatory_fields=[Energy],
    mandatory_variables=[SpinChannel],  # ?
    iri='http://fairmat-nfdi.eu/taxonomy/HomoLumoGap',
    description="""
    The energy difference between the highest occupied spin state
    and the lowest unoccupied spin state.
    """,
)


ElectronicBandGap = DatasetTemplate(
    name='ElectronicBandGap',
    mandatory_fields=[Energy],
    mandatory_variables=[SpinChannel],  # ?
)


BandGapType = ValuesTemplate(
    mandatory_fields=MEnum('direct', 'indirect', 'unknown'),
    description="""
    Type categorization of the electronic band gap. This quantity is directly related with `momentum_transfer` as by
    definition, the electronic band gap is `'direct'` for zero momentum transfer (or if `momentum_transfer` is `None`) and `'indirect'`
    for finite momentum transfer.
    """,
)


ElectronicEigenEnergies = DatasetTemplate(
    name='ElectronicEigenEnergies',  # ? HamiltonianEigenvalues
    mandatory_fields=[Energy, ElectronicStateOccupation],
    mandatory_variables=[SpinChannel],  # ?
    iri='http://fairmat-nfdi.eu/taxonomy/ElectronicEigenvalues',
    description="""
    A base section used to define basic quantities for
    the `ElectronicEigenvalues` and `ElectronicEigenstates` properties.
    """,
)


ElectronicDensityOfStates = DatasetTemplate(
    name='DensityOfStates',
    mandatory_fields=[Energy, ElectronicStateDensity],
    mandatory_variables=[SpinChannel],  # ?
    iri='http://fairmat-nfdi.eu/taxonomy/ElectronicDensityOfStates',
)


ProjectedElectronicDensityOfStates = DatasetTemplate(
    name='ProjectedDensityOfStates',
    mandatory_fields=[Energy, ElectronicStateDensity],
    mandatory_variables=[SpinChannel, ElectronicState],  # ?
    description="""
    The density of states projected on a specific electronic state.
    """,
)


SpectralEnergy = ValuesTemplate(
    name='SpectralEnergy',
    type=np.float64,
    unit='spectral_energy',  # ! TODO: define ureg
    shape=['*'],
    description="""
    Energy values at which the spectral function is calculated.
    """,
)


Spectrum = DatasetTemplate(
    name='Spectrum',
    mandatory_fields=[Count],
    mandatory_variables=[SpectralEnergy],
)


class Variables(ArchiveSection):  # ! TODO: deprecate
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
