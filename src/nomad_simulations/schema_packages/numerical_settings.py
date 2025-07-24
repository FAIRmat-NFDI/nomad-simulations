from itertools import accumulate, chain, tee
from typing import TYPE_CHECKING, Optional, Union

import numpy as np
import pint
from ase.dft.kpoints import get_monkhorst_pack_size_and_offset, monkhorst_pack
from nomad.datamodel.data import ArchiveSection
from nomad.metainfo import JSON, MEnum, Quantity, SubSection
from nomad.units import ureg

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.utils import is_not_representative


class NumericalSettings(ArchiveSection):
    """
    A base section used to define the numerical settings used in a simulation. These are meshes,
    self-consistency parameters, and basis sets.
    """

    name = Quantity(
        type=str,
        description="""
        Name of the numerical settings section. This is typically used to easy identification of the
        `NumericalSettings` section. Possible values: "KMesh", "FrequencyMesh", "TimeMesh",
        "SelfConsistency", "BasisSet".
        """,
    )


class Smearing(NumericalSettings):
    """
    Section specifying the smearing of the occupation numbers to
    either simulate temperature effects or improve SCF convergence.
    """

    name = Quantity(
        type=MEnum('Fermi-Dirac', 'Gaussian', 'Methfessel-Paxton'),
        description="""
        Smearing routine employed.
        """,
    )


class Mesh(ArchiveSection):
    """
    A base section used to define the mesh or space partitioning over which a discrete numerical integration is performed.
    """

    dimensionality = Quantity(
        type=np.int32,
        default=3,
        description="""
        Dimensionality of the mesh: 1, 2, or 3. Defaults to 3.
        """,
    )

    type = Quantity(
        type=MEnum('equidistant', 'logarithmic', 'tangent'),
        shape=['dimensionality'],
        description="""
        Kind of mesh identifying the spacing in each of the dimensions specified by `dimensionality`. It can take the values:

        | Name      | Description                      |
        | --------- | -------------------------------- |
        | `'equidistant'`  | Equidistant grid (also known as 'Newton-Cotes') |
        | `'logarithmic'`  | log distance grid |
        | `'tangent'`  | Non-uniform mesh with tangent spacing, denser near |x|→0, coarser at larger |x| |
        """,
    )

    grid = Quantity(
        type=np.int32,
        shape=['dimensionality'],
        description="""
        Number of points sampled along each axis of the mesh.
        """,
    )

    n_points = Quantity(
        type=np.int32,
        description="""
        Total number of points in the mesh.
        """,
    )

    spacing = Quantity(
        type=np.float64,
        shape=['dimensionality'],
        description="""Grid spacing for equidistant meshes. Ignored for other kinds.
        """,
    )

    points = Quantity(
        type=np.complex128,
        shape=['n_points', 'dimensionality'],
        description="""
        List of all the points in the mesh.
        """,
    )

    multiplicities = Quantity(
        type=np.float64,
        shape=['n_points'],
        description="""
        The amount of times the same point reappears. A value larger than 1, typically indicates
        a symmetry operation that was applied to the `Mesh`.
        """,
    )

    pruning = Quantity(
        type=MEnum('fixed', 'adaptive'),
        description="""
        Pruning method applied for reducing the amount of points in the Mesh. This is typically
        used for numerical integration near the core levels in atoms.
        In the fixed grid methods, the number of angular grid points is predetermined for
        ranges of radial grid points, while in the adaptive methods, the angular grid is adjusted
        on-the-fly for each radial point according to some accuracy criterion.
        Pruning is evaluated on the symmetrised grid.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.dimensionality not in [1, 2, 3]:
            logger.error(
                '`dimensionality` meshes different than 1, 2, or 3 are not supported.'
            )


class NumericalIntegration(NumericalSettings):
    """
    Numerical integration settings used to resolve the following type of integrals by discrete
    numerical integration:

    ```math
    \int_{\vec{r}_a}^{\vec{r}_b} d^3 \vec{r} F(\vec{r}) \approx \sum_{n=a}^{b} w(\vec{r}_n) F(\vec{r}_n)
    ```

    Here, $F$ can be any type of function which would define the type of rules that can be applied
    to solve such integral (e.g., 1D Gaussian quadrature rule or multi-dimensional `angular` rules like the
    Lebedev quadrature rule).

    These multidimensional integral has a `Mesh` defined over which the integration is performed, i.e., the
    $\vec{r}_n$ points.
    """

    mesh = SubSection(sub_section=Mesh.m_def)

    coordinate = Quantity(
        type=MEnum('full', 'radial', 'angular'),
        description="""
        Coordinate over which the integration is performed. `full` means the integration is performed in
        entire space. `radial` and `angular` describe cases where the integration is performed for
        functions which can be splitted into radial and angular distributions (e.g., orbital wavefunctions).
        """,
    )

    integration_rule = Quantity(
        type=MEnum(
            # radial Gaussian rules
            'Gauss-Legendre',  # 1-D
            'Gauss-Chebyshev',
            'Gauss-Lobatto',
            'Gauss-Hermite',
            'Gauss-Laguerre',  # for STO/Slater codes
            'Euler-Maclaurin',  # Murray–Handy–Laming ’93
            'Logarithmic-Log3',  # Mura–Knowles ’96
            'Treutler-Ahlrichs',  # Turbomole M4 mapping
            'Becke-Radial',  # Gauss-Chebyshev (Becke ’88)
            'MultiExp',  # Chien-Gill ’06 (SG-0 parent)
            'Double-Exponential',  # tanh-sinh (SG-2 / SG-3)
            # angular grids
            'Lebedev',  # any (N,θ,φ) order
            'Lebedev-Laikov',  # re-optimisation by Laikov enabling very high orders
            'Product-Legendre',  # Gauss-Legendre θ × uniform φ
            'Becke',  # Becke multicentre partitioning
            'SG-1',  # Gill–Head-Gordon Smolyak grids
            'SG-2',
            'SG-3',
        ),
        description="""
        Integration rule used. This can be any 1D Gaussian quadrature rule or multi-dimensional `angular` rules,
        e.g., Lebedev quadrature rule (see e.g., Becke, Chem. Phys. 88, 2547 (1988)).
        """,
    )

    integration_thresh = Quantity(
        type=np.float64,
        description="""
        An accuracy threshold for the integration grid, controlling how fine the 
        discretization is. Some simulation codes label it "integral accuracy" or "grid accuracy".
        For instance, GRIDTHR in Molpro or BFCut in ORCA.
        """,
    )

    weight_approximation = Quantity(
        type=str,
        description="""
        Approximation applied to the weight when doing the numerical integration.
        See e.g., C. W. Murray, N. C. Handy
        and G. J. Laming, Mol. Phys. 78, 997 (1993).
        """,
    )

    weight_cutoff = Quantity(
        type=np.float64,
        description="""
        Threshold for discarding small weights during integration.
        Grid points very close to the nucleus can have very small grid weights.
        e.g. WEIGHT_CUT in Molpro.
        Wcut in ORCA.
        """,
    )


class KSpaceFunctionalities:
    """
    A functionality class useful for defining methods shared between `KSpace`, `KMesh`, and `KLinePath`.
    """

    def validate_reciprocal_lattice_vectors(
        self,
        reciprocal_lattice_vectors: Optional[pint.Quantity],
        logger: 'BoundLogger',
        check_grid: Optional[bool] = False,
        grid: Optional[list[int]] = [],
    ) -> bool:
        """
        Validate the `reciprocal_lattice_vectors` by checking if they exist and if they have the same dimensionality as `grid`.

        Args:
            reciprocal_lattice_vectors (Optional[pint.Quantity]): The reciprocal lattice vectors of the atomic cell.
            logger (BoundLogger): The logger to log messages.
            check_grid (bool, optional): Flag to check the `grid` is set to True. Defaults to False.
            grid (Optional[list[int]], optional): The grid of the `KMesh`. Defaults to [].

        Returns:
            (bool): True if the `reciprocal_lattice_vectors` exist. If `check_grid_too` is set to True, it also checks if the
            `reciprocal_lattice_vectors` and the `grid` have the same dimensionality. False otherwise.
        """
        if reciprocal_lattice_vectors is None:
            logger.warning('Could not find `reciprocal_lattice_vectors`.')
            return False
        # Only checking the `reciprocal_lattice_vectors`
        if not check_grid:
            return True

        # Checking the `grid` too
        if grid is None:
            logger.warning('Could not find `grid`.')
            return False
        if len(reciprocal_lattice_vectors) != 3 or len(grid) != 3:
            logger.warning(
                'The `reciprocal_lattice_vectors` and the `grid` should have the same dimensionality.'
            )
            return False
        return True

    def resolve_high_symmetry_points(
        self,
        model_systems: list[ModelSystem],
        logger: 'BoundLogger',
        eps: float = 3e-3,
    ) -> Optional[dict]:
        """
        Resolves the `high_symmetry_points` from the list of `ModelSystem`. This method relies on using the `ModelSystem`
        information in the sub-sections `Symmetry` and `AtomicCell`, and uses the ASE package to extract the
        special (high symmetry) points information.

        Args:
            model_systems (list[ModelSystem]): The list of `ModelSystem` sections.
            logger (BoundLogger): The logger to log messages.
            eps (float, optional): Tolerance factor to define the `lattice` ASE object. Defaults to 3e-3.

        Returns:
            (Optional[dict]): The resolved `high_symmetry_points`.
        """
        # Extracting `bravais_lattice` from `ModelSystem.symmetry` section and `ASE.cell` from `ModelSystem.cell`
        lattice = None
        for model_system in model_systems:
            # General checks to proceed with normalization
            if is_not_representative(model_system=model_system, logger=logger):
                continue
            if model_system.symmetry is None:
                logger.warning('Could not find `ModelSystem.symmetry`.')
                continue
            bravais_lattice = [symm.bravais_lattice for symm in model_system.symmetry]
            if len(bravais_lattice) != 1:
                logger.warning(
                    'Could not uniquely determine `bravais_lattice` from `ModelSystem.symmetry`.'
                )
                continue
            bravais_lattice = bravais_lattice[0]

            if model_system.cell is None:
                logger.warning('Could not find `ModelSystem.cell`.')
                continue
            prim_atomic_cell = None
            for atomic_cell in model_system.cell:
                if atomic_cell.type == 'primitive':
                    prim_atomic_cell = atomic_cell
                    break
            if prim_atomic_cell is None:
                logger.warning(
                    'Could not find the primitive `AtomicCell` under `ModelSystem.cell`.'
                )
                continue
            # function defined in ModelSystem
            atoms = model_system.to_ase_atoms(logger=logger)
            cell = atoms.get_cell()
            lattice = cell.get_bravais_lattice(eps=eps)
            break  # only cover the first representative `ModelSystem`

        # Checking if `bravais_lattice` and `lattice` are defined
        if lattice is None:
            logger.warning(
                'Could not resolve `bravais_lattice` and `lattice` ASE object from the `ModelSystem`.'
            )
            return None

        # Non-conventional ordering testing for certain lattices:
        if bravais_lattice in ['oP', 'oF', 'oI', 'oS']:
            a, b, c = lattice.a, lattice.b, lattice.c
            assert a < b
            if bravais_lattice != 'oS':
                assert b < c
        elif bravais_lattice in ['mP', 'mS']:
            a, b, c = lattice.a, lattice.b, lattice.c
            alpha = lattice.alpha * np.pi / 180
            assert a <= c and b <= c  # ordering of the conventional lattice
            assert alpha < np.pi / 2

        # Extracting the `high_symmetry_points` from the `lattice` object
        special_points = lattice.get_special_points()
        if special_points is None:
            logger.warning(
                'Could not find `lattice.get_special_points()` from the ASE package.'
            )
            return None
        high_symmetry_points = {}
        for key, value in lattice.get_special_points().items():
            if key == 'G':
                key = 'Gamma'
            if bravais_lattice == 'tI':
                if key == 'S':
                    key = 'Sigma'
                elif key == 'S1':
                    key = 'Sigma1'
            high_symmetry_points[key] = list(value)
        return high_symmetry_points


class KMesh(Mesh):
    """
    A base section used to specify the settings of a sampling mesh in reciprocal space. The `points` and other
    k-space quantities are defined in units of the reciprocal lattice vectors, so that to obtain their Cartesian coordinates
    value, one should multiply them by the reciprocal lattice vectors (`points_cartesian = points @ reciprocal_lattice_vectors`).
    """

    label = Quantity(
        type=MEnum('k-mesh', 'g-mesh', 'q-mesh'),
        default='k-mesh',
        description="""
        Label used to identify the meaning of the reciprocal grid.
        The actual meaning of `k` vs `g` vs `q` is context-dependent, though typically:
        - `g` is used for the primitive vectors (typically within the Brillouin zone).
        - `k` for a generic reciprocal vector.
        - `q` for any momentum change imparted by a scattering event.
        """,
    )

    center = Quantity(
        type=MEnum('Gamma-centered', 'Monkhorst-Pack', 'Gamma-offcenter'),
        description="""
        Identifier for the center of the Mesh:

        | Name      | Description                      |
        | --------- | -------------------------------- |
        | `'Gamma-centered'` | Regular mesh is centered around Gamma. No offset. |
        | `'Monkhorst-Pack'` | Regular mesh with an offset of half the reciprocal lattice vector. |
        | `'Gamma-offcenter'` | Regular mesh with an offset that is neither `'Gamma-centered'`, nor `'Monkhorst-Pack'`. |
        """,
    )

    offset = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Offset vector shifting the mesh with respect to a Gamma-centered case (where it is defined as [0, 0, 0]).
        """,
    )

    all_points = Quantity(
        type=np.float64,
        shape=['*', 3],
        description="""
        Full list of the mesh points without any symmetry operations in units of the `reciprocal_lattice_vectors`. In the
        presence of symmetry operations, this quantity is a larger list than `points` (as it will contain all the points
        in the Brillouin zone).
        """,
    )

    high_symmetry_points = Quantity(
        type=JSON,
        description="""
        Dictionary containing the high-symmetry point labels and their values in units of `reciprocal_lattice_vectors`.
        E.g., in a cubic lattice:
            high_symmetry_points = {
                'Gamma': [0, 0, 0],
                'X': [0.5, 0, 0],
                'Y': [0, 0.5, 0],
                ...
            ]
        """,
    )

    k_line_density = Quantity(
        type=np.float64,
        unit='m',
        description="""
        Amount of sampled k-points per unit reciprocal length along each axis. Contains the least precise density out of all axes.
        Should only be compared between calculations of similar dimensionality.
        """,
    )

    # TODO add extraction of `high_symmetry_points` using BandStructureNormalizer idea (left for later when defining outputs.py)

    def resolve_points_and_offset(
        self, logger: 'BoundLogger'
    ) -> tuple[Optional[list[np.ndarray]], Optional[np.ndarray]]:
        """
        Resolves the `points` and `offset` of the `KMesh` from the `grid` and the `center`.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (tuple[Optional[list[np.ndarray]], Optional[np.ndarray]]): The resolved `points` and `offset` of the `KMesh`.
        """
        if self.grid is None:
            logger.warning('Could not find `KMesh.grid`.')
            return None, None

        points = None
        offset = None
        if self.center == 'Gamma-centered':  # ! fix this (@ndaelman-hu)
            grid_space = [np.linspace(0, 1, n) for n in self.grid]
            points = np.meshgrid(grid_space)
            offset = np.array([0, 0, 0])
        elif self.center == 'Monkhorst-Pack':
            try:
                points = monkhorst_pack(size=self.grid)
                offset = get_monkhorst_pack_size_and_offset(kpts=points)[-1]
            except ValueError:
                logger.warning(
                    'Could not resolve `KMesh.points` and `KMesh.offset` from `KMesh.grid`. ASE `monkhorst_pack` failed.'
                )
                # this is a quick workaround: k_mesh.grid should be symmetry reduced
                return None, None
        return points, offset

    def get_k_line_density(
        self, reciprocal_lattice_vectors: Optional[pint.Quantity], logger: 'BoundLogger'
    ) -> Optional[np.float64]:
        """
        Gets the k-line density of the `KMesh`. This quantity is used as a precision measure
        of the `KMesh` sampling.

        Args:
            reciprocal_lattice_vectors (pint.Quantity, [3, 3]): Reciprocal lattice vectors of the atomic cell.

        Returns:
            (np.float64): The k-line density of the `KMesh`.
        """
        # Initial check
        if not KSpaceFunctionalities().validate_reciprocal_lattice_vectors(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors,
            logger=logger,
            check_grid=True,
            grid=self.grid,
        ):
            return None

        rlv = reciprocal_lattice_vectors.magnitude
        k_line_density = min(
            [
                k_point / (np.linalg.norm(k_vector))
                for k_vector, k_point in zip(rlv, self.grid)
            ]
        )
        return k_line_density / reciprocal_lattice_vectors.u

    def resolve_k_line_density(
        self,
        model_systems: list[ModelSystem],
        reciprocal_lattice_vectors: pint.Quantity,
        logger: 'BoundLogger',
    ) -> Optional[pint.Quantity]:
        """
        Resolves the `k_line_density` of the `KMesh` from the the list of `ModelSystem`.

        Args:
            model_systems (list[ModelSystem]): The list of `ModelSystem` sections.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[pint.Quantity]): The resolved `k_line_density` of the `KMesh`.
        """
        # Initial check
        if not KSpaceFunctionalities().validate_reciprocal_lattice_vectors(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors,
            logger=logger,
            check_grid=True,
            grid=self.grid,
        ):
            return None

        for model_system in model_systems:
            # General checks to proceed with normalization
            if is_not_representative(model_system=model_system, logger=logger):
                continue
            # TODO extend this for other dimensions (@ndaelman-hu)
            if model_system.type != 'bulk':
                logger.warning('`ModelSystem.type` is not describing a bulk system.')
                continue

            # Resolve `k_line_density`
            if k_line_density := self.get_k_line_density(
                reciprocal_lattice_vectors=reciprocal_lattice_vectors, logger=logger
            ):
                return k_line_density
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # If `grid` is not defined, we do not normalize the KMesh
        if self.grid is None:
            logger.warning('Could not find `KMesh.grid`.')
            return

        # Normalize k mesh from grid sampling
        if self.points is None and self.offset is None:
            self.points, self.offset = self.resolve_points_and_offset(logger=logger)

        # Calculate k_line_density for data quality measures
        model_systems = self.m_xpath(
            'm_parent.m_parent.m_parent.model_system', dict=False
        )
        reciprocal_lattice_vectors = self.m_xpath(
            'm_parent.reciprocal_lattice_vectors', dict=False
        )
        if self.k_line_density is None:
            self.k_line_density = self.resolve_k_line_density(
                model_systems=model_systems,
                reciprocal_lattice_vectors=reciprocal_lattice_vectors,
                logger=logger,
            )

        # Resolve `high_symmetry_points`
        if self.high_symmetry_points is None:
            self.high_symmetry_points = (
                KSpaceFunctionalities().resolve_high_symmetry_points(
                    model_systems=model_systems, logger=logger
                )
            )


class KLinePath(ArchiveSection):
    """
    A base section used to define the settings of a k-line path within a multidimensional mesh. The `points` and other
    k-space quantities are defined in units of the reciprocal lattice vectors, so that to obtain their Cartesian coordinates
    value, one should multiply them by the reciprocal lattice vectors (`points_cartesian = points @ reciprocal_lattice_vectors`).
    """

    high_symmetry_path_names = Quantity(
        type=str,
        shape=['*'],
        description="""
        List of the high-symmetry path names followed in the k-line path. This quantity is directly coupled with `high_symmetry_path_value`.
        E.g., in a cubic lattice: `high_symmetry_path_names = ['Gamma', 'X', 'Y', 'Gamma']`.
        """,
    )

    high_symmetry_path_values = Quantity(
        type=np.float64,
        shape=['*', 3],
        description="""
        List of the high-symmetry path values in units of the `reciprocal_lattice_vectors` in the k-line path. This quantity is directly
        coupled with `high_symmetry_path_names`. E.g., in a cubic lattice: `high_symmetry_path_value = [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0]]`.
        """,
    )

    n_line_points = Quantity(
        type=np.int32,
        description="""
        Number of points in the k-line path.
        """,
    )

    points = Quantity(
        type=np.float64,
        shape=['n_line_points', 3],
        description="""
        List of all the points in the k-line path in units of the `reciprocal_lattice_vectors`.
        """,
    )

    def resolve_high_symmetry_path_values(
        self,
        model_systems: list[ModelSystem],
        reciprocal_lattice_vectors: pint.Quantity,
        logger: 'BoundLogger',
    ) -> Optional[list[float]]:
        """
        Resolves the `high_symmetry_path_values` of the `KLinePath` from the `high_symmetry_path_names`.

        Args:
            model_systems (list[ModelSystem]): The list of `ModelSystem` sections.
            reciprocal_lattice_vectors (pint.Quantity): The reciprocal lattice vectors of the atomic cell.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[list[float]]): The resolved `high_symmetry_path_values`.
        """
        # Initial check on the `reciprocal_lattice_vectors`
        if not KSpaceFunctionalities().validate_reciprocal_lattice_vectors(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors, logger=logger
        ):
            return []

        # Resolving the dictionary containing the `high_symmetry_points` for the given ModelSystem symmetry
        high_symmetry_points = KSpaceFunctionalities().resolve_high_symmetry_points(
            model_systems=model_systems, logger=logger
        )
        if high_symmetry_points is None:
            return []

        # Appending into a list which is stored in the `high_symmetry_path_values`. There is a check in the `normalize()`
        # function to ensure that the length of the `high_symmetry_path_names` and `high_symmetry_path_values` coincide.
        if self.high_symmetry_path_names is None:
            return []
        high_symmetry_path_values = [
            high_symmetry_points[name]
            for name in self.high_symmetry_path_names
            if name in high_symmetry_points.keys()
        ]
        return high_symmetry_path_values

    def validate_high_symmetry_path(self, logger: 'BoundLogger') -> bool:
        """
        Validate `high_symmetry_path_names` and `high_symmetry_path_values` by checking if they are defined and have the same length.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            (bool): True if the `high_symmetry_path_names` and `high_symmetry_path_values` are defined and have the same length, False otherwise.
        """
        if (
            self.high_symmetry_path_names is None
            or self.high_symmetry_path_values is None
        ) or (
            len(self.high_symmetry_path_names) == 0
            or len(self.high_symmetry_path_values) == 0
        ):
            logger.warning(
                'Could not find `KLinePath.high_symmetry_path_names` or `KLinePath.high_symmetry_path_values`.'
            )
            return False
        if len(self.high_symmetry_path_names) != len(self.high_symmetry_path_values):
            logger.warning(
                'The length of `KLinePath.high_symmetry_path_names` and `KLinePath.high_symmetry_path_values` should coincide.'
            )
            return False
        return True

    def get_high_symmetry_path_norms(
        self,
        reciprocal_lattice_vectors: Optional[pint.Quantity],
        logger: 'BoundLogger',
    ) -> Optional[list[pint.Quantity]]:
        """
        Get the high symmetry path points norms from the list of dictionaries of vectors in units of the `reciprocal_lattice_vectors`.
        The norms are accummulated, such that the first high symmetry point in the path list has a norm of 0, while the others sum the
        previous norm. This function is useful when matching lists of points passed as norms to the high symmetry path in order to
        resolve `KLinePath.points`.

        Args:
            reciprocal_lattice_vectors (Optional[np.ndarray]): The reciprocal lattice vectors of the atomic cell.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[list[pint.Quantity]]): The high symmetry points norms list, e.g. in a cubic lattice:
                `high_symmetry_path_value_norms = [0, 0.5, 0.5 + 1 / np.sqrt(2), 1 + 1 / np.sqrt(2)]`
        """
        # Checking the high symmetry path quantities
        if not self.validate_high_symmetry_path(logger=logger):
            return None
        # Checking if `reciprocal_lattice_vectors` is defined and taking its magnitude to operate
        if reciprocal_lattice_vectors is None:
            return None
        rlv = reciprocal_lattice_vectors.magnitude

        def calc_norms(
            value_rlv: np.ndarray, prev_value_rlv: np.ndarray
        ) -> pint.Quantity:
            value_tot_rlv = value_rlv - prev_value_rlv
            return np.linalg.norm(value_tot_rlv) * reciprocal_lattice_vectors.u

        # Compute `rlv` projections
        rlv_projections = list(
            map(lambda value: value @ rlv, self.high_symmetry_path_values)
        )

        # Create two iterators for the projections
        rlv_projections_1, rlv_projections_2 = tee(rlv_projections)

        # Skip the first element in the second iterator
        next(rlv_projections_2, None)

        # Calculate the norms using accumulate
        norms = accumulate(
            zip(rlv_projections_2, rlv_projections_1),
            lambda acc, value_pair: calc_norms(value_pair[0], value_pair[1]) + acc,
            initial=0.0 * reciprocal_lattice_vectors.u,
        )
        return list(norms)

    def resolve_points(
        self,
        points_norm: Union[np.ndarray, list[float]],
        reciprocal_lattice_vectors: Optional[np.ndarray],
        logger: 'BoundLogger',
    ) -> None:
        """
        Resolves the `points` of the `KLinePath` from the `points_norm` and the `reciprocal_lattice_vectors`. This is useful
        when a list of points norms and the list of dictionaries of the high symmetry path are passed to resolve the `KLinePath.points`.

        Args:
            points_norm (list[float]): List of points norms in the k-line path.
            reciprocal_lattice_vectors (Optional[np.ndarray]): The reciprocal lattice vectors of the atomic cell.
            logger (BoundLogger): The logger to log messages.
        """
        # General checks for quantities
        if not self.validate_high_symmetry_path(logger=logger):
            return None
        if reciprocal_lattice_vectors is None:
            logger.warning(
                'The `reciprocal_lattice_vectors` are not passed as an input.'
            )
            return None

        # Check if `points_norm` is a list and convert it to a numpy array
        if isinstance(points_norm, list):
            points_norm = np.array(points_norm)

        # Define `n_line_points`
        if self.n_line_points is not None and len(points_norm) != self.n_line_points:
            logger.info(
                'The length of the `points` and the stored `n_line_points` do not coincide. We will overwrite `n_line_points` with the new length of `points`.'
            )
        self.n_line_points = len(points_norm)

        # Calculate the norms in the path and find the closest indices in points_norm to the high symmetry path norms
        high_symmetry_path_value_norms = self.get_high_symmetry_path_norms(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors, logger=logger
        )
        closest_indices = list(
            map(
                lambda norm: (np.abs(points_norm - norm.magnitude)).argmin(),
                high_symmetry_path_value_norms,
            )
        )

        def linspace_segments(
            prev_value: np.ndarray, value: np.ndarray, num: int
        ) -> np.ndarray:
            return np.linspace(prev_value, value, num=num + 1)[:-1]

        # Generate point segments using `map` and `linspace_segments`
        points_segments = list(
            map(
                lambda i, value: linspace_segments(
                    self.high_symmetry_path_values[i - 1],
                    value,
                    closest_indices[i] - closest_indices[i - 1],
                )
                if i > 0
                else np.array([]),
                range(len(self.high_symmetry_path_values)),
                self.high_symmetry_path_values,
            )
        )
        # and handle the last segment to include all points
        points_segments[-1] = np.linspace(
            self.high_symmetry_path_values[-2],
            self.high_symmetry_path_values[-1],
            num=closest_indices[-1] - closest_indices[-2] + 1,
        )

        # Flatten the list of segments into a single list of points
        new_points = list(chain.from_iterable(points_segments))

        # And store this information in the `points` quantity
        if self.points is not None:
            logger.info('Overwriting `KLinePath.points` with the resolved points.')
        self.points = new_points

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolves `high_symmetry_path_values` from `high_symmetry_path_names`
        model_systems = self.m_xpath(
            'm_parent.m_parent.m_parent.model_system', dict=False
        )
        reciprocal_lattice_vectors = self.m_xpath(
            'm_parent.reciprocal_lattice_vectors', dict=False
        )
        if (
            self.high_symmetry_path_values is None
            or len(self.high_symmetry_path_values) == 0
        ):
            self.high_symmetry_path_values = self.resolve_high_symmetry_path_values(
                model_systems=model_systems,
                reciprocal_lattice_vectors=reciprocal_lattice_vectors,
                logger=logger,
            )

        # If `high_symmetry_path` is not defined, we do not normalize the KLinePath
        if not self.validate_high_symmetry_path(logger=logger):
            return


class KSpace(NumericalSettings):
    """
    A base section used to specify the settings of the k-space. This section contains two main sub-sections,
    depending on the k-space sampling: `k_mesh` or `k_line_path`.
    """

    # ! This needs to be normalized first in order to extract the `reciprocal_lattice_vectors` from the `ModelSystem.cell` information
    reciprocal_lattice_vectors = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='1/meter',
        description="""
        Reciprocal lattice vectors of the simulated cell, in Cartesian coordinates and
        including the $2 pi$ pre-factor. The first index runs over each lattice vector. The
        second index runs over the $x, y, z$ Cartesian coordinates.
        """,
    )

    k_mesh = SubSection(sub_section=KMesh.m_def, repeats=True)

    k_line_path = SubSection(sub_section=KLinePath.m_def)

    def __init__(self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        # Set the name of the section
        self.name = self.m_def.name

    def resolve_reciprocal_lattice_vectors(
        self, model_systems: list[ModelSystem], logger: 'BoundLogger'
    ) -> Optional[pint.Quantity]:
        """
        Resolve the `reciprocal_lattice_vectors` of the `KSpace` from the representative `ModelSystem` section.

        Args:
            model_systems (list[ModelSystem]): The list of `ModelSystem` sections.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[pint.Quantity]): The resolved `reciprocal_lattice_vectors` of the `KSpace`.
        """
        for model_system in model_systems:
            # General checks to proceed with normalization
            if is_not_representative(model_system=model_system, logger=logger):
                continue

            # TODO extend this for other dimensions (@ndaelman-hu)
            if model_system.type is not None and model_system.type != 'bulk':
                logger.warning('`ModelSystem.type` is not describing a bulk system.')
                continue

            atomic_cell = model_system.cell
            if atomic_cell is None:
                logger.warning('`ModelSystem.cell` was not found.')
                continue

            # Set the `reciprocal_lattice_vectors` using ASE
            ase_atoms = model_system.to_ase_atoms(logger=logger)
            return 2 * np.pi * ase_atoms.get_reciprocal_cell() / ureg.angstrom
        return None

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Resolve `reciprocal_lattice_vectors` from the `ModelSystem` ASE object
        model_systems = self.m_xpath('m_parent.m_parent.model_system', dict=False)
        if self.reciprocal_lattice_vectors is None:
            self.reciprocal_lattice_vectors = self.resolve_reciprocal_lattice_vectors(
                model_systems=model_systems, logger=logger
            )


class SelfConsistency(NumericalSettings):
    """
    A base section used to define the convergence settings of self-consistent field (SCF) calculation.
    It determines the conditions for `is_scf_converged` in `SCFOutputs` (see outputs.py). The convergence
    criteria covered are:

        1. The number of iterations is smaller than or equal to `n_max_iterations`.
        2. The total change between two subsequent self-consistent iterations for an output property is below
        `threshold_change`.
    """

    # TODO add examples or MEnum?
    scf_minimization_algorithm = Quantity(
        type=str,
        description="""
        Specifies the algorithm used for self consistency minimization.
        """,
    )

    n_max_iterations = Quantity(
        type=np.int32,
        description="""
        Specifies the maximum number of allowed self-consistent iterations. The simulation `is_scf_converged`
        if the number of iterations is not larger or equal than this quantity.
        """,
    )

    threshold_change = Quantity(
        type=np.float64,
        description="""
        Specifies the threshold for the change between two subsequent self-consistent iterations on
        a given output property. The simulation `is_scf_converged` if this total change is below
        this threshold.
        """,
    )

    threshold_change_unit = Quantity(
        type=str,
        description="""
        Unit using the pint UnitRegistry() notation for the `threshold_change`.
        """,
    )

    def __init__(self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        # Set the name of the section
        self.name = self.m_def.name
