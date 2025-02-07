import numpy as np
from nomad.metainfo.metainfo import Quantity


# ! these quantities cannot be re-used

virial_tensor = Quantity(
    type=np.float64,
    unit='joule',
    shape=['*', '*'],
    description="""
    A measure of the distribution of internal forces and the overall stress within
    a system of particles. Mathematically, the virial tensor is defined as minus the sum
    of the dot product between the position and force vectors for each particle.
    The `VirialTensor` can be related to the non-ideal pressure of the system through
    the virial theorem.
    """,
)

force = Quantity(
    type=np.float64,
    unit='newton',
    shape=['*'],
    description="""
    The force contribution.
    """,
)

pressure = Quantity(
    type=np.float64,
    unit='pascal',
    description="""
    Force exerted per unit area.
    """, # ? what area is referred to
)

volume = value = Quantity(
    type=np.float64,
    unit='m ** 3',
    description="""
    """,
)  # ? hyper-volume

mass_density = Quantity(
    type=np.float64,
    unit='kg / m ** 3',
    description="""
    Mass per unit volume of a material.
    """,
)

temperature = Quantity(
    type=np.float64,
    unit='kelvin',
    description="""
    Measure of the average kinetic energy of the particles in a system.
    """,
)

entropy = Quantity(
    type=np.float64,
    unit='joule / kelvin',
    description="""
    A measure of the disorder or randomness in a system.

    From a thermodynamic perspective, `Entropy` is a measure of the system's energy
    dispersal at a specific temperature, and can be interpreted as the unavailability of
    a system's thermal energy for conversion into mechanical work. For a reversible
    process, the change in `Entropy` is given mathematically by an integral over the
    infinitesimal `Heat` (i.e., thermal energy transferred into the system) divided by the
    `Temperature`.

    From a statistical mechanics viewpoint, entropy quantifies the number of microscopic
    configurations (microstates) that correspond to a thermodynamic system's macroscopic
    state, as given by the Boltzmann equation for entropy.
    """,
) # ?

heat_capacity = Quantity(
    type=np.float64,
    unit='joule / kelvin',
    description="""
    """,
) # ?

hessian = Quantity(
    type=np.float64,
    unit='joule / m ** 2',
    shape=['*', '*'],
    description="""
    A square matrix of second-order partial derivatives of a potential energy function,
    describing the local curvature of the energy surface.
    """,
)
