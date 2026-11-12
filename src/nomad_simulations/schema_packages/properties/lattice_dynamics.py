from nomad.metainfo import MEnum, Quantity

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.spectral_profile import (
    SpectralProfile,
)


class BornEffectiveCharges(PhysicalProperty):
    """
    Born effective charges quantify how much the electronic cloud fails to follow an ion's displacement, thereby creating a macroscopic polarization dipole per unit displacement.

    They contain one value for each atom and direction of displacement.

    It's value is expected to be 0 for non-polar materials.
    """

    value = Quantity(
        type=float,
        unit='elementary_charge',
        description="""
        Value of Born effective charges.
        """,
    )


class InfiniteFrequencyDielectricMatrix(PhysicalProperty):
    """
    The high-frequency dielectric tensor measures how much the electronic cloud polarizes in response to an electric field before the ions have time to move.
    """

    value = Quantity(
        type=float,
        unit='dimensionless',
        description="""
        Value of the high-frequency dielectric tensor.
        """,
    )

    system_dimensionality = Quantity(
        type=MEnum('3D', '2D'),
        description="""
        Dimensionality used in the theoretical description.
        """,
    )


class InteratomicForceConstants(PhysicalProperty):
    """
    Second derivatives of the total energy with respect to the Cartesian displacements of two atoms.
    """

    value = Quantity(
        type=float,
        unit='dimensionless',
        shape=[],
        description="""
        Value of the interatomic constants.
        """,
    )

    # TODO this nees specification
    real_space_decay = Quantity(
        type=float,
        shape=[],
        description="""
        Decay of the interatomic force constants in real space.
        """,
    )

    ewald_parameter = Quantity(
        type=float,
        description="""
        Controls how the Coulombic (or dipolar) interaction is partitioned between long- and short-range contributions.
        """,
    )


class DynamicalMatrix(PhysicalProperty):
    """
    Force-constant matrix that governs how the lattice responds to infinitesimal atomic displacements.

    Fourier-transform of the interatomic force constants.
    """

    value = Quantity(
        type=float,
        unit='eV/angstrom**2',
        shape=[],
        description="""
        Values of the dynamical matrix.
        """,
    )


class MassWeightedDynamicalMatrix(DynamicalMatrix):
    """
    Mass-weighted force-constant matrix that governs how the lattice responds to infinitesimal atomic displacements.

    Fourier-transform of the interatomic force constants.
    """

    value = Quantity(
        type=float,
        unit='eV/(angstrom**2*amu)',
        shape=[],
        description="""
        Values of the dynamical matrix.
        """,
    )


class PhononDensityOfStates(SpectralProfile):
    """
    Density of phonon states.
    """


class PhononBandStructure(PhysicalProperty):
    """
    Band structure of phonons.
    """

    n_bands = Quantity(
        type=int,
        shape=[],
        description="""
        Number of phonon bands. Must be equal to 3 times the number of atoms.
        """,
    )

    n_imaginary_frequencies = Quantity(
        type=int,
        shape=[],
        description="""
        Number of modes with imaginary frequencies. Any number different from 0 indicates instabilitites.
        Obtained by diagonalizatiob of the dynamical matrix with interatomic force constants.
        """,
    )

    value = Quantity(
        type=float,
        unit='joule',
        shape=['*', '*'],
        description="""
        Value of the phonon bands.
        """,
    )
