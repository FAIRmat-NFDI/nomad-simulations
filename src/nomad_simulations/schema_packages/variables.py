from typing import TYPE_CHECKING

import numpy as np
from nomad.metainfo import MEnum, Quantity
from nomad.metainfo.datasets import (
    ValuesTemplate,
    DatasetTemplate,
    Energy,
    Count,
    Temperature,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger


Pressure = ValuesTemplate(
    type=np.float64,
    unit='pascal',
    iri = 'http://fairmat-nfdi.eu/taxonomy/Pressure'
)


Volume = ValuesTemplate(
    type=np.float64,
    unit='m ** 3',
    iri = 'http://fairmat-nfdi.eu/taxonomy/Volume'
)


MassDensity = ValuesTemplate(
    type=np.float64,
    unit='kg / m ** 3',
)


Entropy = ValuesTemplate(
    type=np.float64,
    unit='joule / kelvin',
    description="""A measure of the disorder or randomness in a system.

    From a thermodynamic perspective, `Entropy` is a measure of the system's energy
    dispersal at a specific temperature, and can be interpreted as the unavailability of
    a system's thermal energy for conversion into mechanical work. For a reversible
    process, the change in `Entropy` is given mathematically by an integral over the
    infinitesimal `Heat` (i.e., thermal energy transfered into the system) divided by the
    `Temperature`.

    From a statistical mechanics viewpoint, entropy quantifies the number of microscopic
    configurations (microstates) that correspond to a thermodynamic system's macroscopic
    state, as given by the Boltzmann equation for entropy.
    """
)


HeatCapacity = ValuesTemplate(
    type=np.float64,
    unit='joule / kelvin',
    description="""Amount of heat to be supplied to a material to produce a unit change in its temperature.
    """
)


VirialTensor = ValuesTemplate(
    type=np.float64,
    shape=['*', '*'],
    unit='joule',
    description="""
    A measure of the distribution of internal forces and the overall stress within
    a system of particles. Mathematically, the virial tensor is defined as minus the sum
    of the dot product between the position and force vectors for each particle.
    The `VirialTensor` can be related to the non-ideal pressure of the system through
    the virial theorem.
    """
)


Hessian = ValuesTemplate(
    type=np.float64,
    shape=['*', '*'],
    unit='joule / m ** 2',
    description="""
    A square matrix of second-order partial derivatives of a potential energy function,
    describing the local curvature of the energy surface.
    """
)


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
)  # ! change name


SpinChannel = ValuesTemplate(
    name='SpinChannel',
    type=MEnum('alpha', 'beta', 'both'),
    # ! iri
)  # ? SpinState too

EnergyType = ValuesTemplate(
    type=MEnum(
        'work',
        'internal',
        'free',
        'zero_point',
        'entropy',
        'enthalpy',
        'gibbs free energy',
        'helmholtz free energy',
        'chemical potential',
        'heat',
    ),
)  # ? parallel ValuesTemplate

Force = ValuesTemplate(
    type=np.float64,
    shape=['*'],
    unit='newton',
)

MethodReference = ValuesTemplate(
    type=Reference(ModelMethod),
    description="""
    Reference to a `ModelMethod` definition, according to which the energy was calculated.
    """,
)


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
    mandatory_variables=[SpinChannel],  # ? not relevant to exp.
)  # reference to electronic structure


BandGapType = ValuesTemplate(
    type=MEnum('direct', 'indirect', 'unknown'),
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


ElectronicBandStructure = DatasetTemplate(
    name='ElectronicBandStructure',
    mandatory_fields=[Energy, ElectronicStateOccupation],
    mandatory_variables=[KMomentumTransfer, SpinChannel],  # ?
)


ElectronicDensityOfStates = DatasetTemplate(
    name='DensityOfStates',
    mandatory_fields=[Count],
    mandatory_variables=[Energy, SpinChannel],  # ?
    iri='http://fairmat-nfdi.eu/taxonomy/ElectronicDensityOfStates',
)


ProjectedElectronicDensityOfStates = DatasetTemplate(
    name='ProjectedDensityOfStates',
    mandatory_fields=[Count],
    mandatory_variables=[Energy, SpinChannel, ElectronicState],  # ?
    description="""
    The density of states projected on a specific electronic state.
    """,
)


Spectrum = ValuesTemplate(
    name='Spectrum',
    type=np.float64,
    unit='m',  # ? smaller scale
    shape=['*'],
    description="""
    Wavelength of the spectral entity.
    """,
)


SpectralCount = DatasetTemplate(
    name='SpectralCount',
    mandatory_fields=[Count],
    mandatory_variables=[Spectrum],
)


import abc
class SpectrumConverter(abc.ABC):
    def from_wavelength(self, wavelengths: pint.Quantity) -> pint.Quantity:
        return wavelengths

    @abc.abstractmethod
    def from_frequency(self, frequencies: pint.Quantity) -> pint.Quantity:
        pass

    @abc.abstractmethod
    def from_energy(self, energies: pint.Quantity) -> pint.Quantity:
        pass

    def convert(self, values: pint.Quantity) -> pint.Quantity:
        if not isinstance(values, pint.Quantity):
            raise ValueError("SpectrumConverter requires a pint.Quantity object.")
        to = {
            'wavelength': self.from_wavelength,
            'frequency': self.from_frequency,
            'energy': self.from_energy,
        }
        return to[values.dimensionality](values)
    
    def __call__(self, *args, **kwds):
        if len(args) == 1:
            return self.convert(args[0])


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
