import numpy as np
from nomad.metainfo import MEnum, Quantity

from nomad_simulations.schema_packages.physical_property import PhysicalProperty
from nomad_simulations.schema_packages.properties.spectral_profile import (
    SpectralProfile,
)


class BornEffectiveCharges(PhysicalProperty):
    """
    Born effective charges quantify how much the electronic cloud fails to follow an
    ion's displacement, thereby creating a macroscopic polarization dipole
    per unit displacement.

    This quantity is defined as a tensor for each atom, describing the polariziability
    in each direction following the displacemant in each direction.
    """

    value = Quantity(
        type=float,
        unit='C',
        shape=[3, 3],
        description="""
        Value of Born effective charges.
        """,
    )


class InfiniteFrequencyDielectricTensor(PhysicalProperty):
    """
    The infinite-frequency dielectric tensor measures how much the electronic cloud polarizes 
    in response to an electric field without including contribution from ionic displacement.
    """

    value = Quantity(
        type=float,
        unit='dimensionless',
        shape=[3,3],
        description="""
        Value of the infinite-frequency dielectric tensor.
        """,
    )

    system_dimensionality = Quantity(
        type=MEnum('3D', '2D'),
        description="""
        Spatial dimensionality of the physical system (2D or 3D) for which the high-frequency dielectric tensor is reported. 
        In either case. the dielectric responses differ in their macroscopic definitions and treatment of electrostatic screening.
        """,
    )


class InteratomicForceConstants(PhysicalProperty):
    """
    Second derivatives of the total energy with respect to the Cartesian displacements of two atoms.
    """

    value = Quantity(
        type=float,
        unit='J/meter**2',
        shape=[3,3],
        description="""
        Value of the interatomic force constants.
        """,
    )

    # TODO this needs specification
    real_space_decay = Quantity(
        type=float,
        shape=[],
        description="""
        Decay of the interatomic force constants in real space.
        """,
    )

    ewald_parameter = Quantity(
        type=float,
        unit='1/meter',
        description="""
        Controls how the Coulombic (or dipolar) interaction is partitioned between long- and short-range contributions.
        """,
    )


class DynamicalMatrix(PhysicalProperty):
    """
    Dynamical matrix evaluated at specified phonon wave vectors (q_vector).
    Fourier-transform of the interatomic force constants.
    """


    n_degrees_of_freedom = Quantity(
        type=int,
        description="""
        Number of Cartesian degrees of freedom, equal to three
        times the number of atoms in the primitive cell.
        """,
    )

    value = Quantity(
        type=np.complex64,
        unit='J/m**2',
        shape=['n_degrees_of_freedom', 'n_degrees_of_freedom'],
        description="""
        Complex dynamical matrix at a given phonon wave vector.
        """,
    )

    q_vector = Quantity(
        type=float,
        unit="1/meter",
        shape=[3],
        description="""
        Phonon wave vector for which the dynamical matrix was calculated.
        """
    )

    is_mass_weighted = Quantity(
        type=bool,
        description="""
        Describes if the values of the matrix is mass-weighted or not.
        """
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
        unit='1/s',
        shape=['*', '*'],
        description="""
        Value of the phonon bands.
        """,
    )
