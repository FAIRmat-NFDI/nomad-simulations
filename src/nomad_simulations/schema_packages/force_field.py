import re
import typing

# from structlog.stdlib import BoundLogger
import numpy as np
from ase.dft.kpoints import get_monkhorst_pack_size_and_offset, monkhorst_pack
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.metainfo import (
    JSON,
    URL,
    Context,
    MEnum,
    Quantity,
    Section,
    SubSection,
)
from nomad.units import ureg
from scipy.interpolate import UnivariateSpline

from nomad_simulations.schema_packages.model_method import BaseModelMethod, ModelMethod

MOL = 6.022140857e23
FF_TOL = 1e-2


class ParameterEntry(ArchiveSection):
    """
    Generic section defining a parameter name and value
    """

    name = Quantity(
        type=str,
        shape=[],
        description="""
        Name of the parameter.
        """,
    )

    value = Quantity(
        type=str,
        shape=[],
        description="""
        Value of the parameter as a string.
        """,
    )

    unit = Quantity(
        type=str,
        shape=[],
        description="""
        Unit of the parameter as a string.
        """,
    )


#     # TODO add description quantity


class Potential(BaseModelMethod):
    """
    Section containing information about an interaction potential.

        name: str - potential name, can be as specific as needed
        type: str - potential type, e.g., 'bond', 'angle', 'dihedral', 'improper dihedral', 'nonbonded'
        functional_form: str - functional form of the potential, e.g., 'harmonic', 'Morse', 'Lennard-Jones'
        external_reference: URL
    """

    parameters = SubSection(
        sub_section=ParameterEntry.m_def,
        repeats=True,
        description="""
        List of parameters for custom potentials.
        """,
    )

    type = Quantity(
        type=MEnum(
            'bond',
            'angle',
            'bond-angle',
            'dihedral',
            'angle-dihedral',
            'improper dihedral',
            'nonbonded',
        ),
        shape=[],
        description="""
        Denotes the classification of the interaction.
        """,
    )

    # ? Use Enum here as well?
    functional_form = Quantity(
        type=str,
        shape=[],
        description="""
        Specifies the functional form of the interaction potential, e.g., harmonic, Morse, Lennard-Jones, etc.
        """,
    )

    n_interactions = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description="""
        Total number of interactions in the system for this potential.
        """,
    )

    n_particles = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Number of particles interacting via (each instance of) this potential.
        """,
    )

    particle_labels = Quantity(
        type=np.dtype(str),
        shape=['n_interactions', 'n_particles'],
        description="""
        Labels of the particles for each instance of this potential, stored as a list of tuples.
        """,
    )

    particle_indices = Quantity(
        type=np.int32,
        shape=['n_interactions', 'n_particles'],
        description="""
        Indices of the particles for each instance of this potential, stored as a list of tuples.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        # set the dimensions based on the particle indices, if stored
        if not self.n_interactions:
            self.n_interactions = (
                len(self.particle_indices)
                if self.particle_indices is not None
                else None
            )
        if not self.n_particles:
            self.n_particles = (
                len(self.particle_indices[0])
                if self.particle_indices is not None
                else None
            )

        # check the consistency of the dimensions of the particle indices and labels
        if self.n_interactions and self.n_particles:
            if self.particle_indices is not None:
                assert len(self.particle_indices) == self.n_interactions
                assert len(self.particle_indices[0]) == self.n_particles
            if self.particle_labels is not None:
                assert len(self.particle_labels) == self.n_interactions
                assert len(self.particle_labels[0]) == self.n_particles


class TabulatedPotential(Potential):
    """
    Abstract class for tabulated potentials. The value of the potential and/or force
    is stored for a set of corresponding bin distances. The units for bins and forces
    should be set in the individual subclasses.
    """

    bins = Quantity(
        type=np.float64,
        shape=['*'],
        description="""
        List of bin angles.
        """,
    )

    energies = Quantity(
        type=np.float64,
        unit='J',
        shape=['*'],
        description="""
        List of energy values associated with each bin.
        """,
    )

    forces = Quantity(
        type=np.float64,
        shape=['*'],
        description="""
        List of force values associated with each bin.
        """,
    )

    def compute_forces(self, bins, energies, smoothing_factor=None):
        if smoothing_factor is None:
            smoothing_factor = len(bins) - np.sqrt(2 * len(bins))

        spline = UnivariateSpline(bins, energies, s=smoothing_factor)
        forces = -1.0 * spline.derivative()(bins)

        return forces

    def compute_energies(self, bins, forces, smoothing_factor=None):
        if smoothing_factor is None:
            smoothing_factor = len(bins) - np.sqrt(2 * len(bins))

        spline = UnivariateSpline(bins, forces, s=smoothing_factor)
        energies = -1.0 * np.array([spline.integral(bins[0], x) for x in bins])
        energies -= np.min(energies)

        return energies

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'TabulatedPotential'
        if not self.functional_form:
            self.functional_form = 'tabulated'
        elif self.functional_form != 'tabulated':
            logger.warning(f'Incorrect functional form set for {self.name}.')

        if self.bins is not None and self.energies is not None:
            if len(self.bins) != len(self.energies):
                logger.error(
                    f'bins and energies values have different length in {self.name}'
                )
        if self.bins is not None and self.forces is not None:
            if len(self.bins) != len(self.forces):
                logger.error(f'bins and forces have different length in {self.name}')

        if self.bins is not None:
            smoothing_factor = len(self.bins) - np.sqrt(2 * len(self.bins))
            if self.forces is None and self.energies is not None:
                if not isinstance(self.bins, ureg.Quantity) or not isinstance(
                    self.energies, ureg.Quantity
                ):
                    logger.warning(
                        'Unable to derive tabulated forces from energies, '
                        'bins or energies do not have units.'
                    )
                    return

                try:
                    # generate forces from energies numerically using spline
                    self.forces = (
                        self.compute_forces(
                            self.bins.magnitude,
                            self.energies.magnitude,
                            smoothing_factor=smoothing_factor,
                        )
                        * self.energies.units
                        / self.bins.units
                    )
                    # re-derive energies to check consistency of the forces
                    energies = (
                        self.compute_energies(
                            self.bins.magnitude,
                            self.forces.magnitude,
                            smoothing_factor=smoothing_factor,
                        )
                        * self.energies.units
                    )

                    energies_diff = energies.to('kJ').magnitude * MOL - (
                        self.energies.to('kJ').magnitude * MOL
                        - np.min(self.energies.to('kJ').magnitude * MOL)
                    )
                    if np.all([np.abs(x) < FF_TOL for x in energies_diff]):
                        logger.warning(
                            f'Tabulated forces were generated from energies in {self.name},'
                            f'with consistency errors less than tol={FF_TOL}. '
                        )
                    else:
                        logger.warning(
                            f'Unable to derive tabulated forces from energies in {self.name},'
                            f'consistency errors were greater than tol={FF_TOL}.'
                        )
                        self.forces = None
                except ValueError as e:
                    logger.warning(
                        f'Unable to derive tabulated forces from energies in {self.name},'
                        f'Unkown error occurred in derivation: {e}'
                    )

            if self.forces is not None and self.energies is None:
                if not isinstance(self.bins, ureg.Quantity) or not isinstance(
                    self.forces, ureg.Quantity
                ):
                    logger.warning(
                        'Unable to derive tabulated energies from forces, '
                        'bins or forces do not have units.'
                    )
                    return
                try:
                    # generated energies from forces numerically using spline
                    self.energies = self.compute_energies(
                        self.bins.magnitude,
                        self.forces.magnitude,
                        smoothing_factor=smoothing_factor,
                    )
                    # re-derive forces to check consistency of the energies
                    forces = (
                        self.compute_forces(
                            self.bins.magnitude,
                            self.energies.magnitude,
                            smoothing_factor=smoothing_factor,
                        )
                        * self.forces.units
                    )

                    forces_diff = forces.to(f'kJ/{self.bins.units}').magnitude * MOL - (
                        self.forces.to(f'kJ/{self.bins.units}').magnitude * MOL
                    )
                    if np.all([np.abs(x) < FF_TOL for x in forces_diff]):
                        logger.warning(
                            f'Tabulated energies were generated from forces in {self.name},'
                            f'with consistency errors less than tol={FF_TOL}. '
                        )
                    else:
                        logger.warning(
                            f'Unable to derive tabulated energies from forces in {self.name},'
                            f'consistency errors were greater than tol={FF_TOL}.'
                        )
                        self.energies = None
                except ValueError as e:
                    logger.warning(
                        f'Unable to derive tabulated energies from forces in {self.name},'
                        f'Unkown error occurred in derivation: {e}'
                    )


class PolynomialForceConstant(ParameterEntry):
    """
    Section defining a force constant for a potential of polynomial form.
    """

    name = Quantity(
        type=str,
        shape=[],
        description="""
        Name of the force constant.
        """,
    )

    exponent = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Exponent for this term in the polynomial.
        """,
    )

    value = Quantity(
        type=np.float64,
        shape=[],
        description="""
        Value of the force constant.
        """,
    )


class PolynomialPotential(Potential):
    r"""
    Abstract class for potentials with polynomial form:
    $V(x) = [\left k_1 (x - x_0) + k_2 (x - x_0)^2 + x_3 (x - x_0)^3 + \dots + C$,
    where $\{x_1, x_2, x_3 \dots}$ are the `force_constants` for each term in the polynomial
    expression and $x_0$ is the `equilibrium_value` of $x$. $C$ is an arbitrary constant (not stored).
    This class is intended to be used with another class specifying the potential type, e.g., BondPotential, AnglePotential, etc.
    """

    force_constants = SubSection(
        sub_section=PolynomialForceConstant.m_def,
        repeats=True,
        description="""
        List of force constants value and corresponding unit for polynomial potentials.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'PolynomialPotential'
        if not self.functional_form:
            self.functional_form = 'polynomial'
        elif self.functional_form != 'polynomial':
            logger.warning('Incorrect functional form set for PolynomialPotential.')


class BondPotential(Potential):
    """
    Section containing information about bond potentials.

    Suggested types are: harmonic, cubic, polynomial, Morse, fene, tabulated
    """

    equilibrium_value = Quantity(
        type=np.float64,
        unit='m',
        shape=[],
        description="""
        Specifies the equilibrium bond distance.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        shape=[],
        unit='J / m **2',
        description="""
        Specifies the force constant of the bond potential.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        if not self.name:
            self.name = 'BondPotential'
        if not self.type:
            self.type = 'bond'
        elif self.type != 'bond':
            logger.warning('Incorrect type set for BondPotential.')

        if self.n_particles:
            if self.n_particles != 2:
                logger.warning('Incorrect number of particles set for BondPotential.')
            else:
                self.n_particles = 2


class HarmonicBond(BondPotential):
    r"""
    Section containing information about a Harmonic bond potential:
    $V(r) = \frac{1}{2} k_r (r - r_0)^2 + C$,
    where $k_r$ is the `force_constant` and $r_0$ is the `equilibrium_value` of $r$.
    $C$ is an arbitrary constant (not stored).
    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'HarmonicBond'
        if not self.functional_form:
            self.functional_form = 'harmonic'
        elif self.functional_form != 'harmonic':
            logger.warning('Incorrect functional form set for HarmonicBond.')


class CubicBond(BondPotential):
    r"""
    Section containing information about a Cubic bond potential:
    $V(r) = \frac{1}{2} k_r (r - r_0)^2 + \frac{1}{3} k_c (r - r_0)^3 + C$,
    where $k_r$ is the (harmonic) `force_constant`, $k_c$ is the `force_constant_cubic`,
    and $r_0$ is the `equilibrium_value` of $r$.
    C is an arbitrary constant (not stored).
    """

    force_constant_cubic = Quantity(
        type=np.float64,
        shape=[],
        unit='J / m**3',
        description="""
        Specifies the cubic force constant of the bond potential.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'CubicBond'
        if not self.functional_form:
            self.functional_form = 'cubic'
        elif self.functional_form != 'cubic':
            logger.warning('Incorrect functional form set for CubicBond.')


class PolynomialBond(PolynomialPotential, BondPotential):
    """
    Section containing information about a polynomial bond potential:
    """

    def __init__(self):
        super().__init__()
        docstring = PolynomialPotential.__doc__
        pattern = r'\$V\(x\)(.*?)(\(not stored\)\.)'
        match = re.search(pattern, docstring, re.DOTALL)
        extracted_text = '<functional form missing>'
        if match:
            extracted_text = match.group().strip()  # .group(1).strip()
        self.__doc__ = rf"""{self.__doc__} {extracted_text}.
            Here the dependent variable of the potential, $x$, corresponds to the bond distance."""

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'PolynomialBond'


class MorseBond(BondPotential):
    r"""
    Section containing information about a Morse potential:
    $V(r) = D \left[ 1 - e^{-a(r - r_0)} \right]^2 + C$,
    where $a = sqrt(k/2D)$ is the `well_steepness`, with `force constant` k.
    D is the `well_depth`, and r_0 is the `equilibrium_value` of a.
    C is an arbitrary constant (not stored).
    """

    well_depth = Quantity(
        type=np.float64,
        unit='J',
        shape=[],
        description="""
        Specifies the depth of the potential well.
        """,
    )

    well_steepness = Quantity(
        type=np.float64,
        unit='1/m',
        shape=[],
        description="""
        Specifies the steepness of the potential well.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'MorseBond'
        if not self.functional_form:
            self.functional_form = 'morse'
        elif self.functional_form != 'morse':
            logger.warning('Incorrect functional form set for MorseBond.')

        if self.well_depth is not None and self.well_steepness is not None:
            self.force_constant = 2.0 * self.well_depth * self.well_steepness**2
        elif self.well_depth is not None and self.force_constant is not None:
            self.well_steepness = np.sqrt(self.force_constant / (2.0 * self.well_depth))


class FeneBond(BondPotential):
    r"""
    Section containing information about a FENE potential:
    $V(r) = -\frac{1}{2} k R_0^2 \ln \left[ 1 - \left( \frac{r - r_0}{R_0} \right)^2 \right] + C$,
    $k$ is the `force_constant`, $r_0$ is the `equilibrium_value` of $r$, and $R_0$ is the
    maximum allowable bond extension beyond $r_0$. $C$ is an arbitrary constant (not stored).
    """

    maximum_extension = Quantity(
        type=np.float64,
        unit='m',
        shape=[],
        description="""
        Specifies the maximum extension beyond the equilibrium bond distance.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'FeneBond'
        if not self.functional_form:
            self.functional_form = 'fene'
        elif self.functional_form != 'fene':
            logger.warning('Incorrect functional form set for FeneBond.')


class TabulatedBond(TabulatedPotential, BondPotential):
    """
    Section containing information about a tabulated bond potential.
    The value of the potential and/or force is stored for a set of corresponding bin distances.
    """

    bins = Quantity(
        type=np.float64,
        unit='m',
        shape=['*'],
        description="""
        List of bin distances.
        """,
    )

    forces = Quantity(
        type=np.float64,
        unit='J/m',
        shape=['*'],
        description="""
        List of force values associated with each bin.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'TabulatedBond'


class AnglePotential(Potential):
    """
    Section containing information about angle potentials.

    Suggested types are: harmonic, cosine, restricted_cosine, fourier_series, urey_bradley, polynomial, tabulated
    """

    equilibrium_value = Quantity(
        type=np.float64,
        unit='radian',
        shape=[],
        description="""
        Specifies the equilibrium angle.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        shape=[],
        unit='J / radian**2',
        description="""
        Specifies the force constant of the angle potential.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'AnglePotential'
        if not self.type:
            self.type = 'angle'
        elif self.type != 'angle':
            logger.warning('Incorrect type set for AnglePotential.')

        if self.n_particles:
            if self.n_particles != 3:
                logger.warning('Incorrect number of particles set for AnglePotential.')
            else:
                self.n_particles = 3


class LinearAngle(AnglePotential):
    r"""
    Section containing information about a linear angle potential:
    $V(\theta) = k_\theta (\theta - \theta_0) + C$,
    where $k_\theta$ is the `force_constant` and $\theta_0$ is the `equilibrium_value`.
    $C$ is an arbitrary constant (not stored).
    """

    force_constant = Quantity(
        type=np.float64,
        shape=[],
        unit='J / radian',
        description="""
        Specifies the force constant of the angle potential.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'LinearAngle'
        if not self.functional_form:
            self.functional_form = 'linear'
        elif self.functional_form != 'linear':
            logger.warning('Incorrect functional form set for LinearAngle.')


class HarmonicAngle(AnglePotential):
    r"""
    Section containing information about a Harmonic angle potential:
    $V(\theta) = \frac{1}{2} k_\theta (\theta - \theta_0)^2 + C$,
    where $k_\theta$ is the `force_constant` and $\theta_0$ is the `equilibrium_value` of
    the angle $\theta$. $C$ is an arbitrary constant (not stored).
    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'HarmonicAngle'
        if not self.functional_form:
            self.functional_form = 'harmonic'
        elif self.functional_form != 'harmonic':
            logger.warning('Incorrect functional form set for HarmonicAngle.')


class CosineAngle(AnglePotential):
    r"""
    Section containing information about a Cosine angle potential:
    $V(\theta) = \frac{1}{2} k_\theta \left[ \cos(\theta) - \cos(\theta_0) \right]^2 + C$,
    where $k_\theta$ is the `force_constant` and $\theta_0$ is the `equilibrium_value` of
    the angle $\theta$. $C$ is an arbitrary constant (not stored).

    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'CosineAngle'
        if not self.functional_form:
            self.functional_form = 'cosine'
        elif self.functional_form != 'cosine':
            logger.warning('Incorrect functional form set for CosineAngle.')


class RestrictedCosineAngle(AnglePotential):
    r"""
    Section containing information about a Restricted Cosine angle potential:
    $V(\theta) = \frac{1}{2} k_\theta \frac{\left[ \cos(\theta) - \cos(\theta_0) \right]^2}{\sin^2(\theta)} + C$,
    where $k_\theta$ is the `force_constant` and $\theta_0$ is the `equilibrium_value` of
    the angle $\theta$. $C$ is an arbitrary constant (not stored).

    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'RestrictedCosineAngle'
        if not self.functional_form:
            self.functional_form = 'restricted_cosine'
        elif self.functional_form != 'restricted_cosine':
            logger.warning('Incorrect functional form set for RestrictedCosineAngle.')


# TODO I think we should name these more generally and then say that AKA
class UreyBradleyAngle(AnglePotential):
    r"""
    Section containing information about a Urey-Bradley angle potential:
    $V(\theta) = \frac{1}{2} k_\theta (\theta - \theta_0)^2 +
    \frac{1}{2} k_{13} (r_{13} - r_{13}^0)^2 + C$,
    where where $k_\theta$ is the `force_constant` and $\theta_0$ is the `equilibrium_value` of
    the angle $\theta$, as for a harmonic angle potential. $k_{13}$ is the `force_constant_UB`
    for the 1-3 term, and $r_{13}^0$ is the `equilibrium_value_UB` of the 1-3 distance (i.e.,
    the distance between the edge particles forming the 1-2-3 angle, $\theta$), $r_{13}$.
    $C$ is an arbitrary constant (not stored).
    """

    equilibrium_value_UB = Quantity(
        type=np.float64,
        unit='m',
        shape=[],
        description="""
        Specifies the equilibrium 1-3 distance.
        """,
    )

    force_constant_UB = Quantity(
        type=np.float64,
        shape=[],
        unit='J / m **2',
        description="""
        Specifies the force constant of the potential.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'UreyBradleyAngle'
        if not self.functional_form:
            self.functional_form = 'urey_bradley'
        elif self.functional_form != 'urey_bradley':
            logger.warning('Incorrect functional form set for UreyBradleyAngle.')


class PolynomialAngle(PolynomialPotential, AnglePotential):
    """
    Section containing information about a polynomial angle potential:
    """

    def __init__(self):
        super().__init__()
        docstring = PolynomialPotential.__doc__
        pattern = r'\$V\(x\)(.*?)(\(not stored\)\.)'
        match = re.search(pattern, docstring, re.DOTALL)
        extracted_text = '<functional form missing>'
        if match:
            extracted_text = match.group().strip()  # .group(1).strip()
        self.__doc__ = rf"""{self.__doc__} {extracted_text}.
            Here the dependent variable of the potential, $x$, corresponds to the angle between three particles."""

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'PolynomialAngle'


class TabulatedAngle(AnglePotential, TabulatedPotential):
    """
    Section containing information about a tabulated bond potential. The value of the potential and/or force
    is stored for a set of corresponding bin distances.
    """

    bins = Quantity(
        type=np.float64,
        unit='radian',
        shape=['*'],
        description="""
        List of bin angles.
        """,
    )

    forces = Quantity(
        type=np.float64,
        unit='J/radian',
        shape=['*'],
        description="""
        List of force values associated with each bin.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'TabulatedAngle'


class BondAngleCouplingPotential(Potential):
    """
    Section containing information about bond potentials.

    Suggested types are: linear
    """

    equilibrium_bond_length = Quantity(
        type=np.float64,
        unit='m',
        shape=[],
        description="""
        Equilibrium bond length $r_0$.
        """,
    )

    equilibrium_angle = Quantity(
        type=np.float64,
        unit='radian',
        shape=[],
        description="""
        Equilibrium angle $\theta_0$.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        unit='J / (m * radian)',
        shape=[],
        description="""
        Force constant coupling bond length and angle.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'BondAngleCouplingPotential'
        if not self.type:
            self.type = 'bond-angle'
        elif self.type != 'bond-angle':
            logger.warning('Incorrect type set for BondAngleCouplingPotential.')

        if self.n_particles:
            if self.n_particles != 3:
                logger.warning(
                    'Incorrect number of particles set for BondAngleCouplingPotential.'
                )
            else:
                self.n_particles = 3


class LinearBondAngleCoupling(BondAngleCouplingPotential):
    r"""
    Section containing a linear bond–angle coupling potential:
    $V(r, \theta) = k (r - r_0)(\theta - \theta_0) + C$,
    where $r_0$ and $\theta_0$ are the equilibrium values.
    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'LinearBondAngleCoupling'
        if not self.functional_form:
            self.functional_form = 'linear'
        elif self.functional_form != 'linear':
            logger.warning('Incorrect functional form set for LinearBondAngleCoupling.')


class DihedralPotential(Potential):
    """
    Section containing information about dihedral potentials.

    Suggested types are: fourier_series, tabulated

    # ? Something about angle convention?
    """

    equilibrium_value = Quantity(
        type=np.float64,
        unit='radian',
        shape=[],
        description="""
        Specifies the equilibrium dihedral angle.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        shape=[],
        unit='J / radian**2',
        description="""
        Specifies the force constant of the dihedral angle potential.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'DihedralPotential'
        if not self.type:
            self.type = 'dihedral'
        elif self.type != 'dihedral':
            logger.warning('Incorrect type set for DihedralPotential.')

        if self.n_particles:
            if self.n_particles != 4:
                logger.warning(
                    'Incorrect number of particles set for DihedralPotential.'
                )
            else:
                self.n_particles = 4


class PeriodicDihedral(DihedralPotential):
    r"""
    Section for periodic proper dihedral potential:
    $V(\phi) = \frac{1}{2} k [1 + \cos(n \phi - \delta)] + C$
    """

    multiplicity = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Periodicity $n$.
        """,
    )

    phase_shift = Quantity(
        type=np.float64,
        unit='radian',
        shape=[],
        description="""
        Phase shift $\delta$.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        unit='J',
        shape=[],
        description="""
        Amplitude $k$.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'PeriodicDihedral'
        if not self.functional_form:
            self.functional_form = 'periodic'


class RyckaertBellemansDihedral(DihedralPotential):
    r"""
    Ryckaert-Bellemans dihedral:
    $V(\phi) = \sum_{n=0}^{5} C_n \cos^n(\phi)$
    """

    coefficients = Quantity(
        type=np.float64,
        shape=[6],
        unit='J',
        description="""
        Coefficients $C_0$ through $C_5$.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'RyckaertBellemansDihedral'
        if not self.functional_form:
            self.functional_form = 'ryckaert_bellemans'


class TabulatedDihedral(DihedralPotential, TabulatedPotential):
    """
    Section containing information about a tabulated bond potential. The value of the potential and/or force
    is stored for a set of corresponding bin distances.
    """

    bins = Quantity(
        type=np.float64,
        unit='radian',
        shape=['*'],
        description="""
        List of bin dihedral angles.
        """,
    )

    forces = Quantity(
        type=np.float64,
        unit='J/radian',
        shape=['*'],
        description="""
        List of force values associated with each bin.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'TabulatedDihedral'


class AngleDihedralCouplingPotential(Potential):
    """
    Section containing information about angle-dihedral potentials.

    Suggested types are: linear
    """

    equilibrium_angle = Quantity(type=np.float64, unit='radian', shape=[])
    equilibrium_dihedral = Quantity(type=np.float64, unit='radian', shape=[])
    force_constant_angle = Quantity(type=np.float64, unit='J/radian**2', shape=[])
    force_constant_dihedral = Quantity(type=np.float64, unit='J/radian**2', shape=[])
    coupling_constant = Quantity(type=np.float64, unit='J/radian**2', shape=[])

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'AngleDihedralCouplingPotential'
        if not self.type:
            self.type = 'angle-dihedral'
        elif self.type != 'angle-dihedral':
            logger.warning('Incorrect type set for AngleDihedralCouplingPotential.')

        if self.n_particles:
            if self.n_particles != 4:
                logger.warning(
                    'Incorrect number of particles set for AngleDihedralCouplingPotential.'
                )
            else:
                self.n_particles = 4


class HarmonicAngleDihedralCoupling(AngleDihedralCouplingPotential):
    """
    Harmonic form of an angle–dihedral coupling potential:
    $V = k_1(\theta - \theta_0)^2 + k_2(\phi - \phi_0)^2 + k_3(\theta - \theta_0)(\phi - \phi_0)$
    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'HarmonicAngleDihedralCoupling'
        if not self.functional_form:
            self.functional_form = 'angle_dihedral_coupled'
        elif self.functional_form != 'angle_dihedral_coupled':
            logger.warning(
                'Incorrect functional form set for HarmonicAngleDihedralCoupling.'
            )


class ImproperDihedralPotential(DihedralPotential):
    """
    Section containing information about improper dihedral potentials.

    Suggested types are: ...

    # ? Something about angle convention?
    """

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)
        self.name = 'ImproperDihedralPotential'
        if self.type != 'improper dihedral':
            self.type = 'improper dihedral'


class HarmonicImproper(ImproperDihedralPotential):
    r"""
    Section for harmonic improper dihedral potential:
    $V(\omega) = \frac{1}{2} k (\omega - \omega_0)^2 + C$
    """

    equilibrium_value = Quantity(
        type=np.float64,
        unit='radian',
        shape=[],
        description="""
        Equilibrium improper angle $\omega_0$.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        unit='J / radian**2',
        shape=[],
        description="""
        Force constant $k$.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'HarmonicImproper'
        if not self.functional_form:
            self.functional_form = 'harmonic'


class PeriodicImproper(ImproperDihedralPotential):
    r"""
    Section for periodic improper dihedral potential:
    $V(\omega) = \frac{1}{2} k [1 + \cos(n \omega - \delta)] + C$
    """

    multiplicity = Quantity(
        type=np.int32,
        shape=[],
        description="""
        Periodicity $n$.
        """,
    )

    phase_shift = Quantity(
        type=np.float64,
        unit='radian',
        shape=[],
        description="""
        Phase shift $\delta$.
        """,
    )

    force_constant = Quantity(
        type=np.float64,
        unit='J',
        shape=[],
        description="""
        Amplitude $k$.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'PeriodicImproper'
        if not self.functional_form:
            self.functional_form = 'periodic'


class ForceField(ModelMethod):
    """
    Section containing the parameters of a (classical, particle-based) force field model.
    Typical `numerical_settings` are ForceCalculations.
    Lists of interactions by type and, if available, corresponding parameters can be given within `interactions`.
    Additionally, a published model can be referenced with `reference`.
    """

    # name and external reference already defined in BaseModelMethod
    # name = Quantity(
    #     type=str,
    #     shape=[],
    #     description="""
    #     Identifies the name of the model.
    #     """,
    # )

    # reference = Quantity(
    #     type=str,
    #     shape=['0..*'],
    #     description="""
    #     List of references to the model e.g. DOI, URL.
    #     """,
    # )

    kimid = Quantity(
        type=URL,
        description="""
        Reference to a model stored on the OpenKim database.
        """,
        a_eln=ELNAnnotation(component='URLEditQuantity'),
    )

    #     interactions = SubSection(sub_section=Interactions.m_def, repeats=True)
    contributions = SubSection(
        sub_section=Potential.m_def,
        repeats=True,
        description="""
        Contribution or sub-term of the total model Hamiltonian.
        """,
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        self.name = 'ForceField'
        logger.warning('in force field')


# TODO Need to survey Lammps and maybe openmm and check for other common potential types
# TODO prevent the base classes from being used directly as they won't pass norm
# without units
