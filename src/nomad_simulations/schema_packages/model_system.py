#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import re
from functools import lru_cache
from hashlib import sha1
from typing import TYPE_CHECKING, Optional

import ase
import numpy as np
from ase.symbols import symbols2numbers
from matid import Classifier, SymmetryAnalyzer  # pylint: disable=import-error
from matid.classification.classifications import (
    Atom,
    Class0D,
    Class1D,
    Class2D,
    Class3D,
    Material2D,
    Surface,
)
from nomad.atomutils import Formula, get_normalized_wyckoff, search_aflow_prototype
from nomad.config import config
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.basesections.v2 import Entity, System
from nomad.metainfo import MEnum, Quantity, SectionProxy, SubSection
from nomad.units import ureg

from nomad_simulations.schema_packages.data_types import Bound, m_int_bounded
from nomad_simulations.schema_packages.utils import log

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any, Callable, Optional

    import pint
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    CGBeadState,
    ParticleState,
)
from nomad_simulations.schema_packages.utils import (
    catch_not_implemented,
    get_sibling_section,
    is_not_representative,
)

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


class GeometricSpace(Entity):
    """
    A base section used to define geometrical spaces and their entities.
    """

    length_vector_a = Quantity(
        type=np.float64,
        unit='meter',
        description="""
        Length of the first basis vector.
        """,
    )

    length_vector_b = Quantity(
        type=np.float64,
        unit='meter',
        description="""
        Length of the second basis vector.
        """,
    )

    length_vector_c = Quantity(
        type=np.float64,
        unit='meter',
        description="""
        Length of the third basis vector.
        """,
    )

    angle_vectors_b_c = Quantity(
        type=np.float64,
        unit='radian',
        description="""
        Angle between second and third basis vector.
        """,
    )

    angle_vectors_a_c = Quantity(
        type=np.float64,
        unit='radian',
        description="""
        Angle between first and third basis vector.
        """,
    )

    angle_vectors_a_b = Quantity(
        type=np.float64,
        unit='radian',
        description="""
        Angle between first and second basis vector.
        """,
    )

    volume = Quantity(
        type=np.float64,
        unit='meter ** 3',
        description="""
        Volume of a 3D real space entity.
        """,
    )

    surface_area = Quantity(
        type=np.float64,
        unit='meter ** 2',
        description="""
        Surface area of a 3D real space entity.
        """,
    )

    area = Quantity(
        type=np.float64,
        unit='meter ** 2',
        description="""
        Area of a 2D real space entity.
        """,
    )

    length = Quantity(
        type=np.float64,
        unit='meter',
        description="""
        Total length of a 1D real space entity.
        """,
    )

    coordinates_system = Quantity(
        type=MEnum('cartesian', 'cylindrical', 'spherical', 'ellipsoidal', 'polar'),
        default='cartesian',
        description="""
        Coordinate system used to define geometrical primitives of a shape in real
        space. Defaults to 'cartesian'.

        | name       | description | dimensionalities | coordinates |
        |------------|-------------|------------------|-------------|
        | cartesian  | coordinate system with fixed angles between the axes (not necessarily 90^{\circ}) | 1, 2, 3 | x, y, z |
        | cylindrical| cylindrical symmetry | 3 | r, theta, z |
        | spherical  | spherical symmetry | 3 | r, theta, phi |
        | ellipsoidal| spherically elongated system | 3 | r, theta, phi |
        | polar      | spherical symmetry | 2 | r, theta |
        """,  # ? could this not be extended to the k-space
    )

    origin_shift = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Vector `p` from the origin of a custom coordinates system to the origin of the
        global coordinates system. Together with the matrix `P` (stored in transformation_matrix),
        the transformation between the custom coordinates `x` and global coordinates `X` is then
        given by:
            `x` = `P` `X` + `p`.
        """,
    )  # remove?

    transformation_matrix = Quantity(
        type=np.float64,
        shape=[3, 3],
        description="""
        Matrix `P` used to transform the custom coordinates system to the global coordinates system.
        Together with the vector `p` (stored in origin_shift), the transformation between
        the custom coordinates `x` and global coordinates `X` is then given by:
            `x` = `P` `X` + `p`.
        """,
    )  # remove?


def _check_implemented(func: 'Callable'):
    """
    Decorator to restrict the comparison functions to the same class.
    """

    def wrapper(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return func(self, other)

    return wrapper


class PartialOrderElement:
    def __init__(self, representative_variable):
        self.representative_variable = representative_variable

    def __hash__(self):
        return self.representative_variable.__hash__()

    @_check_implemented
    def __eq__(self, other):
        return self.representative_variable == other.representative_variable

    @_check_implemented
    def __lt__(self, other):
        return False

    @_check_implemented
    def __gt__(self, other):
        return False

    def __le__(self, other):
        return self.__eq__(other)

    def __ge__(self, other):
        return self.__eq__(other)

    # __ne__ assumes that usage in a finite set with its comparison definitions


class HashedPositions(PartialOrderElement):
    # `representative_variable` is a `pint.Quantity` object

    def __hash__(self):
        hash_str = sha1(
            np.ascontiguousarray(
                np.round(
                    self.representative_variable.to_base_units().magnitude,
                    decimals=configuration.equal_cell_positions_tolerance,
                    out=None,
                )
            ).tobytes()
        ).hexdigest()
        return int(hash_str, 16)

    def __eq__(self, other):
        """Equality as defined between HashedPositions."""
        if (
            self.representative_variable is None
            or other.representative_variable is None
        ):
            return NotImplemented
        return np.allclose(self.representative_variable, other.representative_variable)


class Cell(GeometricSpace):
    """
    A base section used to specify the cell quantities of a system at a given moment in time.
    """

    name = Quantity(
        type=str,
        description="""
        Name of the specific cell section. This is typically used to easy identification of the
        `Cell` section. Possible values: "AtomicCell".
        """,
    )

    type = Quantity(
        type=MEnum('original', 'primitive', 'conventional'),
        description="""
        Representation type of the cell structure. It might be:
            - 'original' as in originally parsed,
            - 'primitive' as the primitive unit cell,
            - 'conventional' as the conventional cell used for referencing.
        """,
    )

    n_cell_points = Quantity(
        type=np.int32,
        description="""
        Number of cell points.
        """,
    )

    lattice_vectors = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='meter',
        description="""
        Lattice vectors of the simulated cell in Cartesian coordinates. The first index runs
        over each lattice vector. The second index runs over the $x, y, z$ Cartesian coordinates.
        """,
    )

    periodic_boundary_conditions = Quantity(
        type=bool,
        shape=[3],
        description="""
        If periodic boundary conditions are applied to each direction of the crystal axes.
        """,
    )

    supercell_matrix = Quantity(
        type=np.int32,
        shape=[3, 3],
        description="""
        Specifies the matrix that transforms the primitive unit cell into the supercell in
        which the actual calculation is performed. In the easiest example, it is a diagonal
        matrix whose elements multiply the lattice_vectors, e.g., [[3, 0, 0], [0, 3, 0], [0, 0, 3]]
        is a $3 x 3 x 3$ superlattice.
        """,
    )


class AtomicCell(Cell):
    """
    A base section used to specify the atomic cell information of a system.
    """

    equivalent_atoms = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        List of equivalent atoms as defined in `atoms`. If no equivalent atoms are found,
        then the list is simply the index of each element, e.g.:
            - [0, 1, 2, 3] all four atoms are non-equivalent.
            - [0, 0, 0, 3] three equivalent atoms and one non-equivalent.
        """,
    )

    # ! improve description and clarify whether this belongs to `Symmetry` with @lauri-codes
    wyckoff_letters = Quantity(
        type=str,
        shape=['*'],
        description="""
        Wyckoff letters associated with each atom.
        """,
    )

    @log
    def set_geometric_space_for_atomic_cell(self) -> None:
        """
        Get the real space parameters for the atomic cell using ASE.
        to_ase_atoms live under the parent ModelSystem.

        Args:
            logger (BoundLogger): The logger to log messages.
        """
        logger = self.set_geometric_space_for_atomic_cell.__annotations__['logger']
        parent = self.m_parent
        if not isinstance(parent, ModelSystem):
            logger.warning(
                'Parent is not a ModelSystem → geometric-space normalisation skipped.'
            )
            return

        atoms = parent.to_ase_atoms(logger=logger)
        if atoms is None:
            return  # parent already logged the problem

        try:
            cell = atoms.get_cell()
            self.length_vector_a, self.length_vector_b, self.length_vector_c = (
                cell.lengths() * ureg.angstrom
            )
            self.angle_vectors_b_c, self.angle_vectors_a_c, self.angle_vectors_a_b = (
                cell.angles() * ureg.degree
            )
            self.volume = cell.volume * ureg.angstrom**3
        except Exception as exc:
            logger.warning(
                'Failed to extract geometric-space data from ASE cell.',
                exc_info=exc,
            )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Set the name of the section
        self.name = self.m_def.name if self.name is None else self.name

        # extract all the geometric‐space quantities; errors are logged inside
        self.set_geometric_space_for_atomic_cell(logger=logger)


class GlobalSymmetry(ArchiveSection):
    """
    A base section specifying the global symmetry of the corresponding `ModelSystem` at large,
    which can be used for categorization and lookup. It does not define local, site-specific symmetry.
    """


class GlobalCrystalSymmetry(GlobalSymmetry):
    """
    A symmetry section specialized for identifying bulk crystal space groups.
    All symmetry operators are defined with respect to the **standard crystallographic unit cell**.
    A definition of the orientation of the reference cell is given via `origin_shift` and `transformation_matrix`.

    **References:**
    - Hahn, T. (Ed.). (2005). *International Tables for Crystallography, Volume A: Space-group symmetry* (5th ed.). Springer. https://doi.org/10.1107/97809553602060000001
    - Hall, S.R. (1981). Space-group notation with an explicit origin. *Acta Crystallographica Section A*, 37(4), 517-525. https://doi.org/10.1107/S0108767381001228
    - Togo, A. (2024). Spglib: A Software Library for Crystal Symmetry Search. *arXiv March 13, 2024*. https://doi.org/10.48550/arXiv.1808.01590
    - Curtarolo, S., et al. (2012). AFLOW: An automatic framework for high-throughput materials discovery. *Computational Materials Science*, 58, 218-226.
    - Mehl, M.J., et al. (2017). The AFLOW library of crystallographic prototypes: part 1. *Computational Materials Science*, 136, S1-S828.
    - Strukturbericht volumes (1913-1943). Historical crystallographic structure classification.
    - Pearson's Crystal Data. Comprehensive crystallographic database.
    """

    lattice_type = Quantity(  # called `crystal_system` in `results`
        type=MEnum(
            'a - triclinic',
            'm - monoclinic',
            'o - orthorhombic',
            't - tetragonal',
            'r - trigonal',
            'h - hexagonal',
            'c - cubic',
            'mp - oblique',
            'op - rectangular',
            'oc - centered rectangular',
            'tp - square',
            'hp - hexagonal 2D',
            'ap - linear',
        ),
        description="""
        Bravais lattice type according to the crystal family classification in crystallography.
        This follows the Pearson notation system where the first lowercase letter identifies the
        crystal family based on lattice symmetry (Hahn, 2005):
        
        | Symbol | Crystal Family | Lattice Parameters | Dimensionality |
        |--------|----------------|--------------------|-----------------|
        | a      | triclinic / anorthic | $a \neq b \neq c$, $\alpha \neq \beta \neq \gamma \neq 90^{\circ}$ | 3D |
        | m      | monoclinic     | $a \neq b \neq c$, $\alpha = \gamma = 90^{\circ} \neq \beta$ | 3D |
        | o      | orthorhombic   | $a \neq b \neq c$, $\alpha = \beta = \gamma = 90^{\circ}$ | 3D |
        | t      | tetragonal     | $a = b \neq c$, $\alpha = \beta = \gamma = 90^{\circ}$ | 3D |
        | r      | trigonal       | $a = b = c$, $\alpha = \beta = \gamma \neq 90^{\circ}$ (rhombohedral) or $a = b \neq c$, $\alpha = \beta = 90^{\circ}$, $\gamma = 120^{\circ}$ (hexagonal) | 3D |
        | h      | hexagonal      | $a = b \neq c$, $\alpha = \beta = 90^{\circ}$, $\gamma = 120^{\circ}$ | 3D |
        | c      | cubic          | $a = b = c$, $\alpha = \beta = \gamma = 90^{\circ}$ | 3D |
        | mp     | oblique        | $a \neq b$, $\gamma \neq 90^{\circ}$ | 2D |
        | op     | rectangular    | $a \neq b$, $\gamma = 90^{\circ}$ | 2D |
        | oc     | centered rectangular | $a \neq b$, $\gamma = 90^{\circ}$ | 2D |
        | tp     | square         | $a = b$, $\gamma = 90^{\circ}$ | 2D |
        | hp     | hexagonal 2D   | $a = b$, $\gamma = 120^{\circ}$ | 2D |
        | ap     | linear         | lattice parameter $a$ | 1D |

        **Dimensionality applicability:**
        - 3D: a, b, o, t, r, h, c
        - 2D: mp, op, oc, tp, hp
        - 1D: ap

        **Note:** This quantity is setting-dependent and determined through symmetry analysis.
        For 2D and 1D systems, equivalent notation may be used with appropriate modifications.

        **Reference:** Hahn, T. (2005). International Tables for Crystallography, Volume A: Space-group symmetry. Springer.
        """,
    )  # TODO: leverage text search for query suggestions

    lattice_centering = Quantity(
        type=MEnum(
            'P - primitive',
            'R - rhombohedral',
            'S - face centred',
            'I - body centred',
            'F - all faces centred',
            'c - centered 2D',
            'p - primitive 2D/1D',
        ),
        description="""
        Lattice centering type according to the International Union of Crystallography (IUCr) notation.
        This describes how lattice points are distributed within the conventional unit cell (Hahn, 2005):

        | Symbol | Centering Type | Description | Lattice Points | Dimensionality |
        |--------|----------------|-------------|----------------|----------------|
        | P      | primitive      | lattice points only at cell corners | $(0,0,0)$ | 3D |
        | R      | rhombohedral   | rhombohedral centering (hexagonal setting) | $(0,0,0)$, $(2/3,1/3,1/3)$, $(1/3,2/3,2/3)$ | 3D |
        | S      | face centered  | one pair of opposite faces centered | $(0,0,0)$, $(1/2,1/2,0)$ | 3D |
        | I      | body centered  | body center | $(0,0,0)$, $(1/2,1/2,1/2)$ | 3D |
        | F      | all faces centered | all faces centered | $(0,0,0)$, $(1/2,1/2,0)$, $(1/2,0,1/2)$, $(0,1/2,1/2)$ | 3D |
        | c      | centered 2D    | centered rectangular lattice | $(0,0)$, $(1/2,1/2)$ | 2D |
        | p      | primitive 2D/1D | primitive lattice | $(0,0)$ (2D), $(0)$ (1D) | 2D/1D |

        **Dimensionality applicability:**
        - 3D: P, R, S, I, F
        - 2D: p, c
        - 1D: p

        **Compatibility with lattice types:**
        - Triclinic (a): P only
        - Monoclinic (b): P, S
        - Orthorhombic (o): P, S, I, F
        - Tetragonal (t): P, I
        - Trigonal (r): P, R (in hexagonal setting)
        - Hexagonal (h): P only
        - Cubic (c): P, I, F

        **Note:** This quantity is setting-dependent and automatically determined through symmetry analysis.
        For lower-dimensional systems, the centering is interpreted in the context of the reduced dimensionality.

        **Reference:** Hahn, T. (2005). International Tables for Crystallography, Volume A: Space-group symmetry. Springer.
        """,
    )  # TODO: leverage text search for query suggestions

    space_group_symbol = Quantity(
        type=str,
        description="""
        Hermann-Mauguin space group symbol specifying the 3D space group symmetry of this system.
        This notation describes the symmetry operations and lattice type in a standardized format
        established by the International Union of Crystallography (IUCr). The symbol encodes
        the lattice centering (P, A, B, C, I, F, R) followed by point group symmetry elements
        along crystallographic directions.
        
        **Examples:**
            - `P63/mmc`: Primitive hexagonal lattice with 6₃ screw axis and mirror planes
            - `Fm-3m`: Face-centered cubic with inversion and mirror symmetry  
            - `P4/mmm`: Primitive tetragonal with 4-fold rotation and perpendicular mirror planes
            - `Ia-3d`: Body-centered cubic with glide planes and diamond-type symmetry
        
        **Reference:** Hahn, T. (Ed.). (2005). *International Tables for Crystallography, Volume A: Space-group symmetry* (5th ed.). Springer. https://doi.org/10.1107/97809553602060000001
        """,
    )  # TODO: leverage text search for query suggestions

    space_group_number = Quantity(
        type=m_int_bounded(dtype=np.int32, bound=Bound('[1,230]')),
        description="""
        International Union of Crystallography (IUCr) space group number uniquely identifying
        the 3D space group symmetry of this system. These numbers range from 1 to 230,
        corresponding to the complete enumeration of crystallographic space groups in 3D.
        The numbering follows the standard sequence established in the International Tables
        for Crystallography.
        
        **Examples:**
            - `194`: P6₃/mmc (hexagonal)
            - `225`: Fm-3m (face-centered cubic)
            - `123`: P4/mmm (tetragonal)
            - `230`: Ia-3d (body-centered cubic)
        
        **Reference:** Hahn, T. (Ed.). (2005). *International Tables for Crystallography, Volume A: Space-group symmetry* (5th ed.). Springer. https://doi.org/10.1107/97809553602060000001
        """,
    )

    hall_symbol_long = Quantity(  # ? remove
        type=str,
        description="""
        Extended Hall space group symbol providing **complete explicit specification** of the
        space group generators and setting. This expanded notation includes all details about
        generator operations, coordinate systems, and alternative representations that get
        simplified out when creating the short form. The long form serves as the **source**
        from which short Hall symbols are derived.
        
        **Long Hall symbols contain all available information:**
        1. **Complete generator specifications** - full screw/glide details (e.g., `4₃`, `2₁`)
        2. **Explicit origin coordinates** - setting info like `(0 0 1/4)`, `(1/8 1/8 1/8)`
        3. **Axis orientation details** - crystallographic direction assignments
        4. **Alternative generator sets** - equivalent but different generating operations
        5. **Coordinate transformation info** - relationships between settings
        6. **Matrix representations** - explicit rotation and translation components
        
        **Relationship to Short Form:**
        - **Long → Short conversion**: Remove setting info, simplify notation, keep minimal generators
        - **Short → Long expansion**: Add origin choice, explicit screw/glide types, coordinate details
        
        **Conversion Examples:**
        - **Long**: `P 6₃c 2c (0 0 1/4) [c-glides ⊥ to 6₃ axis]` → **Short**: `P 6c 2c`
        - **Long**: `-F 4₃ 2₁ 3₁ (1/8 1/8 1/8) [origin at body center]` → **Short**: `-F 4 2 3`
        - **Long**: `P 4/m 2ab/m 2/m (0 1/2 0) [multiple mirror specs]` → **Short**: `P 4 2`
        
        **Examples:**
        - `P 6₃c 2c (0 0 1/4)`: P6₃/mmc with explicit origin shift and screw axis details
        - `-F 4₃ 2₁ 3₁ (1/8 1/8 1/8)`: Fm-3m with complete screw specifications and origin
        - `P 4ab 2ab -1ab (1/4 1/4 0)`: P4/mmm with detailed glide plane types and origin
        - `-I 4bd 2c 3 (1/4 1/4 1/4) [Alt: -I 4cd 2b 3]`: Ia-3d with alternative generator sets
        
        **Reference:** Hall, S.R. (1981). Space-group notation with an explicit origin. *Acta Crystallographica Section A*, 37(4), 517-525. https://doi.org/10.1107/S0108767381001228
        """,
    )  # TODO: leverage text search for query suggestions

    hall_symbol_short = Quantity(
        type=str,
        description="""
        Hall space group symbol defining the **minimum set of symmetry generators** needed to
        completely specify the space group symmetry and its setting. Unlike Hermann-Mauguin
        symbols which describe symmetry elements along conventional directions, Hall symbols
        explicitly define generator operations and their geometric relationships, making them
        **unambiguous** for computational purposes.
        
        **Short Hall symbols are derived from long forms by:**
        1. **Keeping lattice centering** (P, A, B, C, I, F, R) - always essential
        2. **Extracting minimal generator set** - removing derivable operations  
        3. **Removing origin specifications** - setting info like `(0 0 1/4)`
        4. **Simplifying generator notation** - e.g., `4₃` → `4` if screw type is standard
        5. **Removing alternative notations** - keeping only primary generator form
        6. **Preserving essential glide/screw info** - when it distinguishes the space group
        
        The Hall notation specifies:
        - **Lattice type**: P (primitive), A/B/C (face-centered), I (body-centered), F (face-centered), R (rhombohedral)
        - **Generator operations**: Rotation axes (2, 3, 4, 6), screw axes (2₁, 3₁, 4₁, 6₁, etc.), inversion (-), mirror planes (m), glide planes (a, b, c, n, d)
        - **Setting choice**: Origin and axis orientation that defines the coordinate system
        
        **Conversion Examples:**
        - **Long**: `P 6₃c 2c (0 0 1/4) [c-glides ⊥ to 6₃ axis]` → **Short**: `P 6c 2c`
        - **Long**: `-F 4₃ 2₁ 3₁ (1/8 1/8 1/8) [origin at body center]` → **Short**: `-F 4 2 3`
        - **Long**: `P 4/m 2ab/m 2/m (0 1/2 0) [multiple mirror specs]` → **Short**: `P 4 2`
        
        **Examples:**
        - `P 6c 2c`: P6₃/mmc with c-glide generators along specific directions
        - `-F 4 2 3`: Fm-3m with inversion, 4-fold axis, and 2-fold axes along ⟨110⟩ directions  
        - `P 4 2`: P422 with 4-fold rotation and 2-fold rotations
        - `-I 4bd 2c 3`: Ia-3d with body-centered lattice and specific glide/rotation generators
        
        **Reference:** Hall, S.R. (1981). Space-group notation with an explicit origin. *Acta Crystallographica Section A*, 37(4), 517-525. https://doi.org/10.1107/S0108767381001228
        """,
    )

    hall_number = Quantity(
        type=np.int32,
        description="""
        Hall-type number providing a unique numerical identifier for each distinct
        Hall symbol and its associated setting across all dimensionalities. Unlike
        space/plane/line group numbers which identify the group type, Hall numbers
        distinguish between different settings and origin choices for the same group.
        
        **3D Space Groups**: 
        - 530 distinct Hall symbols (Togo, A. (2024)) corresponding to the 230 space group types
        - Multiple Hall numbers possible for groups with different conventional settings
        - Examples: `525` (Ia-3d), `424` (P6₃/mmc), `123` (Fm-3m setting)
        
        **2D Plane Groups**:
        - Each of the 17 plane groups may have multiple settings
        - Examples: `12` (p4mm), `5` (c2mm setting)
        
        **1D Line Groups**:
        - Each of the 7 line groups typically has one primary setting
        - Examples: `7` (p2mm), `3` (pm)
        
        The numbering system accounts for:
        - **Origin choices**: Different positions of coordinate system origin
        - **Axis orientations**: Various conventional orientations of crystallographic axes
        - **Cell choices**: Alternative unit cell definitions for the same lattice
        - **Setting transformations**: Mathematical relationships between different settings
        
        **Reference:**
        - Hall, S.R. (1981). Space-group notation with an explicit origin. *Acta Crystallographica Section A*, 37(4), 517-525. https://doi.org/10.1107/S0108767381001228
        - Togo, A. (2024): Spglib: A Software Library for Crystal Symmetry Search. *arXiv March 13, 2024*. https://doi.org/10.48550/arXiv.1808.01590

        """,
    )  # TODO: leverage text search for query suggestions

    strukturbericht_designation = Quantity(  # ? drop `designation`
        type=str,
        description="""
        Classification of the material according to the Strukturbericht system, a historical
        classification scheme that groups crystal structures by their structural type and
        coordination environments. This system predates modern space group analysis and
        provides a complementary structural categorization based on prototypical compounds.
        Extracted from the AFLOW encyclopedia of crystallographic prototypes.

        The designation consists of a letter (A, B, C, D, L, etc.) indicating the general
        structural family, followed by a number and sometimes additional letters:
        
        **Common Structure Types:**
        - **A-type**: Simple structures (A1: Cu, A2: W, A3: Mg, A4: diamond)
        - **B-type**: Binary compounds with simple ratios (B1: NaCl, B2: CsCl, B3: ZnS)
        - **C-type**: More complex binary compounds (C1: CaF₂, C15: Cu₂Mg Laves phase)
        - **D-type**: Complex structures (D0₁₉: Ni₃Sn)
        - **L-type**: Ordered alloy structures (L1₀: AuCu, L1₂: Cu₃Au, L2₁: Heusler)
        
        **References:**
        - Strukturbericht volumes (1913-1943)
        - Pearson's Crystal Data
        - AFLOW prototype encyclopedia: https://www.aflowlib.org/prototype-encyclopedia/
        """,
    )

    prototype_formula = Quantity(
        type=str,
        description="""
        Chemical formula of the prototypical material that exemplifies this crystal structure
        type, as catalogued in the AFLOW encyclopedia of crystallographic prototypes. This
        represents the historically first or most well-known compound that exhibits this
        particular structural arrangement.
        
        The formula follows standard chemical notation, with structural
        information encoded through the specific elemental composition and stoichiometry
        of the prototype compound.
        
        **Examples:**
        - `Cu`: Face-centered cubic metals (A1 structure type)
        - `CsCl`: Cesium chloride structure (B2 structure type)
        - `CaF2`: Fluorite structure (C1 structure type)
        - `Cu2MgAl`: Heusler alloy structure (L21 structure type)
        - `Ni3Sn`: D019 structure type
        
        **Reference:**
        - Curtarolo, S., et al. "AFLOW: An automatic framework for high-throughput materials
        discovery." Computational Materials Science 58 (2012): 218-226.
        - AFLOW prototype encyclopedia: https://www.aflowlib.org/prototype-encyclopedia/
        """,
    )

    prototype_aflow_id = Quantity(
        type=str,
        description="""
        Unique identifier for the `prototype_formula` as indexed in the AFLOW encyclopedia of
        crystallographic prototypes. This ID provides direct linkage to the comprehensive
        structural database maintained by the AFLOW consortium.
        
        AFLOW prototype IDs typically follow a systematic naming convention that encodes
        structural information including:
        - Prototype formula
        - Space group information
        - Structural parameters
        - Variant designations
        
        **Examples:**
        - `A1_cF4_225_a`: Face-centered cubic (Cu-type)
        - `B1_cF8_225_a_b`: Rock salt structure (NaCl-type)
        - `C1_cF12_225_a_c`: Fluorite structure (CaF₂-type)
        - `L21_cF16_225_a_b_c`: Heusler structure (Cu₂MnAl-type)
        
        **Reference:**
        - Mehl, M.J., et al. "The AFLOW library of crystallographic prototypes: part 1."
        - Computational Materials Science 136 (2017): S1-S828.
        - AFLOW prototype encyclopedia: https://www.aflowlib.org/prototype-encyclopedia/
        """,  # use more up-to-date AFLOW properties reference
    )

    origin_shift = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Translation of the origin of `ModelSystem.cell` to the conventional unit cell
        that was used to derive the space group symmetry. Is particularly necessary for defining the symmetry operations.
        Is expressed as a vector in the global coordinates system.
        """,
    )

    transformation_matrix = Quantity(
        type=np.float64,
        shape=[3, 3],
        description="""
        Transformation matrix to produce (along with the `origin_shift`) the conventional unit cell
        that was used to derive the space group symmetry. Is particularly necessary for defining the symmetry operations.
        Is expressed as a $3 \times 3$ matrix in the global coordinates system.
        """,
    )

    def _parse_bravais_lattice_pearson(self, pearson_notation: str) -> tuple[str, str]:
        """
        Parse Pearson notation (e.g., 'cF', 'oP') into lattice_type and lattice_centering.

        Args:
            pearson_notation (str): Pearson notation from MatID (e.g., 'cF', 'oP', 'hP')

        Returns:
            tuple[str, str]: (lattice_type, lattice_centering) formatted for the MEnum values
        """
        if not pearson_notation or len(pearson_notation) != 2:
            return None, None

        lattice_symbol = pearson_notation[0].lower()
        centering_symbol = pearson_notation[1].upper()

        # Map lattice symbols to full names
        lattice_map = {
            'a': 'a - triclinic',
            'm': 'm - monoclinic',
            'o': 'o - orthorhombic',
            't': 't - tetragonal',
            'h': 'h - hexagonal',
            'r': 'r - trigonal',
            'c': 'c - cubic',
        }

        # Map centering symbols to full names
        centering_map = {
            'P': 'P - primitive',
            'S': 'S - face centred',
            'I': 'I - body centred',
            'F': 'F - all faces centred',
            'R': 'R - rhombohedral',
        }

        lattice_type = lattice_map.get(lattice_symbol)
        lattice_centering = centering_map.get(centering_symbol)

        return lattice_type, lattice_centering

    @property
    def bravais_lattice(self) -> Optional[str]:
        """
        Reconstruct Pearson notation from lattice_type and lattice_centering for backward compatibility.

        Returns:
            str: Pearson notation (e.g., 'cF', 'oP')
        """
        if not self.lattice_type or not self.lattice_centering:
            return None

        lattice_symbol = (
            self.lattice_type.split(' - ')[0]
            if ' - ' in self.lattice_type
            else self.lattice_type
        )
        centering_symbol = (
            self.lattice_centering.split(' - ')[0]
            if ' - ' in self.lattice_centering
            else self.lattice_centering
        )

        return f'{lattice_symbol}{centering_symbol}'

    def _process_hall_symbols(
        self, symmetry_analyzer: 'SymmetryAnalyzer', logger: 'BoundLogger'
    ) -> dict[str, str | int | None]:
        """
        Process Hall symbols from SymmetryAnalyzer and convert to the new field structure.

        Args:
            symmetry_analyzer: The MatID SymmetryAnalyzer object
            logger: Logger for error reporting

        Returns:
            dict: Dictionary with hall_symbol_short, hall_symbol_long, and hall_number
        """
        hall_data: dict[str, str | int | None] = {}

        try:
            # Get the raw Hall symbol from the analyzer
            hall_symbol_raw = symmetry_analyzer.get_hall_symbol()

            if hall_symbol_raw:
                # Convert raw Hall symbol to short form by removing origin specifications
                # and simplifying notation following the conversion rules
                hall_short = self._convert_hall_long_to_short(hall_symbol_raw)
                hall_data['hall_symbol_short'] = hall_short

                # The raw symbol from spglib is typically already in short form,
                # so we construct a more detailed long form if possible
                hall_long = self._construct_hall_long_form(
                    hall_symbol_raw, symmetry_analyzer
                )
                hall_data['hall_symbol_long'] = hall_long

                # Get Hall number if available (requires mapping from spglib data)
                hall_number = self._get_hall_number(symmetry_analyzer)
                hall_data['hall_number'] = hall_number

            else:
                hall_data['hall_symbol_short'] = None
                hall_data['hall_symbol_long'] = None
                hall_data['hall_number'] = None

        except Exception as e:
            logger.warning(f'Error processing Hall symbols: {e}')
            hall_data['hall_symbol_short'] = None
            hall_data['hall_symbol_long'] = None
            hall_data['hall_number'] = None

        return hall_data

    def _convert_hall_long_to_short(self, hall_symbol: str) -> str:
        """
        Convert a long Hall symbol to short form by applying conversion rules.

        Args:
            hall_symbol: Input Hall symbol (potentially in long form)

        Returns:
            str: Short form Hall symbol
        """
        if not hall_symbol:
            return hall_symbol

        # Apply conversion rules:
        # 1. Remove origin shift specifications (text in parentheses)
        short_form = re.sub(r'\s*\([^)]*\)', '', hall_symbol)

        # 2. Remove explanatory text in brackets
        short_form = re.sub(r'\s*\[[^\]]*\]', '', short_form)

        # 3. Simplify explicit screw axis notations (e.g., 4₃ -> 4 if standard)
        # This is space group dependent, so we keep the subscripts for now

        # 4. Remove redundant generator specifications
        # This requires more sophisticated space group knowledge

        # 5. Clean up extra whitespace
        short_form = re.sub(r'\s+', ' ', short_form.strip())

        return short_form

    def _construct_hall_long_form(
        self, hall_symbol: str, symmetry_analyzer: 'SymmetryAnalyzer'
    ) -> str:
        """
        Construct a more detailed long form Hall symbol with additional setting information.

        Args:
            hall_symbol: Base Hall symbol
            symmetry_analyzer: SymmetryAnalyzer for additional data

        Returns:
            str: Enhanced long form Hall symbol
        """
        if not hall_symbol:
            return hall_symbol

        long_form = hall_symbol

        try:
            # Add origin shift information if available
            origin_shift = symmetry_analyzer._get_spglib_origin_shift()
            if origin_shift is not None and not all(x == 0 for x in origin_shift):
                # Format origin shift as fractional coordinates
                origin_str = f'({origin_shift[0]:.3g} {origin_shift[1]:.3g} {origin_shift[2]:.3g})'
                long_form += f' {origin_str}'

        except Exception:
            # If origin shift is not available, just return the base symbol
            pass

        return long_form

    @log
    def _get_hall_number(self, symmetry_analyzer: 'SymmetryAnalyzer') -> int | None:
        """
        Get the Hall number from the space group mapping in `spglib`.

        Args:
            symmetry_analyzer: `SymmetryAnalyzer` for space group data, preferably run beforehand

        Returns:
            (int | None): Hall number if available (1-530 range)
        """
        # Hall numbers are determined by space group, not atom types
        space_group_number = symmetry_analyzer.get_space_group_number()
        if space_group_number:
            import spglib

            # Get the space group type info which includes the Hall number
            sg_type = spglib.get_spacegroup_type(space_group_number)
            if sg_type and hasattr(sg_type, 'hall_number'):
                hall_number = sg_type.hall_number
                # Validate hall_number is in expected range
                if isinstance(hall_number, int):
                    return hall_number

        return None

    def resolve_bulk_symmetry(
        self, original_atomic_cell: 'AtomicCell', logger: 'BoundLogger'
    ) -> None:
        """
        Resolves the symmetry of the material being simulated via MatID.
        Uses both geometric (lattice) and atomic arrangement (positions + types) data.
        Populates the symmetry properties in `self`.

        Args:
            original_atomic_cell (AtomicCell): The `AtomicCell` section that the symmetry
            uses to in MatID.SymmetryAnalyzer().
            logger (BoundLogger): The logger to log messages.
        """
        try:
            ase_atoms = self.m_parent.to_ase_atoms(logger=logger)
            symmetry_analyzer = SymmetryAnalyzer(
                ase_atoms, symmetry_tol=configuration.symmetry_tolerance
            )
        except ValueError as e:
            logger.debug(
                'Symmetry analysis with MatID is not available.', details=str(e)
            )
            return
        except Exception as e:
            logger.warning('Symmetry analysis with MatID failed.', exc_info=e)
            return

        bravais_lattice_pearson = symmetry_analyzer.get_bravais_lattice()
        lattice_type, lattice_centering = self._parse_bravais_lattice_pearson(
            bravais_lattice_pearson
        )
        self.lattice_type = lattice_type
        self.lattice_centering = lattice_centering

        # Process Hall symbols using the specialized method
        hall_data = self._process_hall_symbols(symmetry_analyzer, logger)
        self.hall_symbol_short = hall_data.get('hall_symbol_short')
        self.hall_symbol_long = hall_data.get('hall_symbol_long')
        self.hall_number = hall_data.get('hall_number')

        self.point_group_symbol = symmetry_analyzer.get_point_group()
        self.space_group_number = symmetry_analyzer.get_space_group_number()
        self.space_group_symbol = (
            symmetry_analyzer.get_space_group_international_short()
        )
        self.origin_shift = symmetry_analyzer._get_spglib_origin_shift()
        self.transformation_matrix = (
            symmetry_analyzer._get_spglib_transformation_matrix()
        )

        # Populating the originally parsed AtomicCell wyckoff_letters and equivalent_atoms information
        original_wyckoff = symmetry_analyzer.get_wyckoff_letters_original()
        original_equivalent_atoms = symmetry_analyzer.get_equivalent_atoms_original()
        original_atomic_cell.wyckoff_letters = original_wyckoff
        original_atomic_cell.equivalent_atoms = original_equivalent_atoms

        # Getting prototype_formula, prototype_aflow_id, and strukturbericht designation from
        # standarized Wyckoff numbers and the space group number
        if self.space_group_number:
            # Retrieve the expanded conventional system (an ASE.Atoms object) from the analyzer.
            conventional_system = symmetry_analyzer.get_conventional_system()
            conventional_num = conventional_system.get_atomic_numbers()
            conventional_wyckoff = symmetry_analyzer.get_wyckoff_letters_conventional()
            norm_wyckoff = get_normalized_wyckoff(
                atomic_numbers=conventional_num, wyckoff_letters=conventional_wyckoff
            )
            aflow_prototype = search_aflow_prototype(
                space_group=self.space_group_number,
                norm_wyckoff=norm_wyckoff,
            )
            if aflow_prototype:
                strukturbericht = aflow_prototype.get('Strukturbericht Designation')
                strukturbericht = (
                    re.sub('[$_{}]', '', strukturbericht)
                    if strukturbericht != 'None'
                    else None
                )
                prototype_aflow_id = aflow_prototype.get('aflow_prototype_id')
                prototype_formula = aflow_prototype.get('Prototype')
                self.strukturbericht_designation = strukturbericht
                self.prototype_aflow_id = prototype_aflow_id
                self.prototype_formula = prototype_formula

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        atomic_cell = get_sibling_section(
            section=self, sibling_section_name='cell', logger=logger
        )
        # TODO : the following is a temporary fix, and it might break again
        # when there are systems with deeper hierarchies.
        if self.m_parent.m_parent is not None and self.m_parent.type == 'bulk':
            # Populate symmetry properties
            self.resolve_bulk_symmetry(original_atomic_cell=atomic_cell, logger=logger)


class ChemicalFormula(ArchiveSection):
    """
    A base section used to store the chemical formulas of a `ModelSystem` in different formats.
    """

    descriptive = Quantity(
        type=str,
        description="""
        The chemical formula of the system as a string to be descriptive of the computation.
        It is derived from `elemental_composition` if not specified, with non-reduced integer
        numbers for the proportions of the elements.
        """,
    )

    reduced = Quantity(
        type=str,
        description="""
        Alphabetically sorted chemical formula with reduced integer chemical proportion
        numbers. The proportion number is omitted if it is 1.
        """,
    )

    iupac = Quantity(
        type=str,
        description="""
        Chemical formula where the elements are ordered using a formal list based on
        electronegativity as defined in the IUPAC nomenclature of inorganic chemistry (2005):

            - https://en.wikipedia.org/wiki/List_of_inorganic_compounds

        Contains reduced integer chemical proportion numbers where the proportion number
        is omitted if it is 1.
        """,
    )

    hill = Quantity(
        type=str,
        description="""
        Chemical formula where Carbon is placed first, then Hydrogen, and then all the other
        elements in alphabetical order. If Carbon is not present, the order is alphabetical.
        """,
    )

    anonymous = Quantity(
        type=str,
        description="""
        Formula with the elements ordered by their reduced integer chemical proportion
        number, and the chemical species replaced by alphabetically ordered letters. The
        proportion number is omitted if it is 1.

        Examples: H2O becomes A2B and H2O2 becomes AB. The letters are drawn from the English
        alphabet that may be extended by increasing the number of letters: A, B, ..., Z, Aa, Ab
        and so on. This definition is in line with the similarly named OPTIMADE definition.
        """,
    )

    def resolve_chemical_formulas(self, formula: Formula) -> None:
        """
        Resolves the chemical formulas of the `ModelSystem` in different formats.

        Args:
            formula (Formula): The Formula object from NOMAD atomutils containing the chemical formulas.
        """
        self.descriptive = formula.format(fmt='descriptive')
        self.reduced = formula.format(fmt='reduced')
        self.iupac = formula.format(fmt='iupac')
        self.hill = formula.format(fmt='hill')
        self.anonymous = formula.format(fmt='anonymous')

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Instead of retrieving a sibling "cell", get the parent ModelSystem
        model_system = self.m_parent
        if model_system is None:
            logger.warning('Could not resolve parent ModelSystem for ChemicalFormula.')
            return

        # Get the ASE Atoms using the ModelSystem.to_ase_atoms() method (which now gathers positions, cell, etc.)
        ase_atoms = model_system.to_ase_atoms(logger=logger)
        if ase_atoms is None:
            logger.error('Could not generate ASE Atoms from the ModelSystem.')
            return

        formula = None
        try:
            formula = Formula(formula=ase_atoms.get_chemical_formula())
        except ValueError as e:
            logger.warning(
                'Could not extract the chemical formulas information.',
                exc_info=e,
                error=str(e),
            )
        if formula:
            self.resolve_chemical_formulas(formula=formula)
            self.m_cache['elemental_composition'] = formula.elemental_composition


class ModelSystem(System):
    """
    Model system used as an input for simulating the material.

    Atom positions at the top level in the quantity “positions”
    and the per‐atom state (including electronic state information) in the subsection “particle_states”.
    Downstream subsystems refer to atoms via particle_indices.

    Definitions:
        - `name` refers to all the verbose and user-dependent naming in ModelSystem,
        - `type` refers to the type of the ModelSystem (atom, bulk, surface, etc.),
        - `dimensionality` refers to the dimensionality of the ModelSystem (0, 1, 2, 3),

    If the ModelSystem `is_representative`, proceeds with normalization. The time evolution of the
    ModelSystem is stored in a `list` format under `Simulation`, and for each element of that list,
    `time_step` can be defined.

    It is composed of the sub-sections:
        - `GlobalSymmetry` containing the information of (sub)system-wide symmetry
        - `ChemicalFormula` containing the information of the chemical formulas in different
        formats.

    This class nests over itself (with the section proxy in `sub_systems`) to define different
    parent-child system trees. The quantities `branch_label`, `branch_depth`, `particle_indices`,
    and `bond_list` are used to define the parent-child tree.

    The normalization is ran in the following order:
        1. `OrbitalsState.normalize()` in atoms_state.py under `AtomsState`
        2. `CoreHole.normalize()` in atoms_state.py under `AtomsState`
        3. `HubbardInteractions.normalize()` in atoms_state.py under `AtomsState`
        4. `AtomsState.normalize()` in atoms_state.py
        5. `AtomicCell.normalize()` in atomic_cell.py
        6. `Symmetry.normalize()` in this class
        7. `ChemicalFormula.normalize()` in this class
        8. `ModelSystem.normalize()` in this class

    Note: `normalize()` can be called at any time for each of the classes without being re-triggered
    by the NOMAD normalization.

    Examples for the subsystem hierarchical trees:

        - Example 1, a crystal Si setup has 0 subsystems.

        - Example 2, a Si/GaAs heterostructure has:
          - 1 top-level `ModelSystem` section (Si/GaAs together)
          - 2 subsystem sections of type `ModelSystem` (for Si and GaAs each).
            As these are considered independent systems, they will have their own `GlobalSymmetry` section.
            A new `AtomicCell` section is defined only when simulation box changes.

        - Example 3, a solution of C800H3200Cu has: 1 top-level `ModelSystem` section (for
        800*(CH4)+Cu) and 2 nested subsystem `ModelSystem` sections (for CH4 and Cu).

        - Example 4, a passivated surface GaAs-CO2 has --> similar to the example 2.

        - Example 5, a passivated heterostructure Si/(GaAs-CO2) has: 1 top-level `ModelSystem`
        section (for Si/(GaAs-CO2)), 2 mid-level subsystem sections (for Si and GaAs-CO2),
        and 2 low-level subsystem sections in the GaAs-CO2 system.
    """

    __is_atomic_flag: Optional[bool] = None

    normalizer_level = 0

    name = Quantity(
        type=str,
        description="""
        Any verbose naming referring to the ModelSystem. Can be left empty if it is a simple
        crystal or it can be filled up. For example, an heterostructure of graphene (G) sandwiched
        in between hexagonal boron nitrides (hBN) slabs could be named 'hBN/G/hBN'.
        """,
    )

    # TODO work on improving and extending this quantity and the description
    # TODO distinguish between molecule and cluster
    type = Quantity(
        type=MEnum(
            'atom',
            'active_atom',
            'molecule',
            'cluster',
            'molecule / cluster',  # this is kept due to MatID Class0D classification
            'monomer',
            '1D',
            'surface',
            '2D',
            'bulk',
            'unavailable',
        ),
        description="""
        Type of the system (atom, bulk, surface, etc.) which is determined by the normalizer.
        """,
    )

    dimensionality = Quantity(
        type=np.int32,
        description="""
        Dimensionality of the system: 0, 1, 2, or 3 dimensions. For atomistic systems this
        is automatically evaluated by using the topology-scaling algorithm:

            https://doi.org/10.1103/PhysRevLett.118.106101.
        """,
    )

    # TODO improve on the definition and usage
    is_representative = Quantity(
        type=bool,
        default=False,
        description="""
        If the model system section is the one representative of the computational simulation.
        Defaults to False and set to True by the `Computation.normalize()`. If set to True,
        the `ModelSystem.normalize()` function is ran (otherwise, it is not).
        """,
    )

    # ? Check later when implementing `Outputs` if this quantity needs to be extended
    time_step = Quantity(
        type=np.int32,
        description="""
        Specific time snapshot of the ModelSystem. The time evolution is then encoded
        in a list of ModelSystems under Computation where for each element this quantity defines
        the time step.
        """,
    )

    cell = SubSection(sub_section=Cell.m_def)

    symmetry = SubSection(sub_section=GlobalSymmetry.m_def)

    chemical_formula = SubSection(sub_section=ChemicalFormula.m_def, repeats=False)

    branch_label = Quantity(
        type=str,
        description="""
        Label of the specific branch in the hierarchical `ModelSystem` tree.
        """,
    )

    branch_depth = Quantity(
        type=np.int32,
        description="""
        Index refering to the depth of a branch in the hierarchical `ModelSystem` tree.
        """,
    )

    particle_indices = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        Global indices of the particles that belong to this subsystem,
        counted from the representative (top-level) ModelSystem.

        **Example (SrTiO_3 primitive cell)**
        parent particle_states   : ['Sr', 'Ti', 'O', 'O', 'O']  # → indices 0-4
        Ti-only subsystem      : particle_indices = [1]
        Ti + apical-O subsystem: particle_indices = [1, 4]
        """,
    )

    n_particles = Quantity(
        type=np.int32,
        description="""
        Number of particles/atoms in the simulation.
        """,
    )

    positions = Quantity(
        type=np.float64,
        shape=['*', 3],
        unit='meter',
        description="""
            Cartesian coordinates of all atoms in the top-level system.
            All subsystems will reference these positions via particle_indices.
        """,
    )

    velocities = Quantity(
        type=np.float64,
        shape=['*', 3],
        unit='meter / second',
        description="""
            Velocities of the particles: I.e., the change in cartesian coordinates of the
        particle position with time.
        """,
    )

    # TODO improve description and add an example
    bond_list = Quantity(
        type=np.int32,
        shape=['*', 2],
        description="""
        List of pairs of atom indices corresponding to bonds (e.g., as defined by a force field)
        within this atoms_group.
        """,
    )

    composition_formula = Quantity(
        type=str,
        description="""
        The overall composition of the system with respect to its subsystems.
        The syntax for a system composed of X and Y with x and y components of each,
        respectively, is X(x)Y(y). At the deepest branch in the hierarchy, the
        composition_formula is expressed in terms of the atomic labels.

        Example: A system composed of 3 water molecules with the following hierarchy

                                TotalSystem
                                    |
                                group_H2O
                                |   |   |
                               H2O H2O H2O

        has the following compositional formulas at each branch:

            branch 0, index 0: "Total_System" composition_formula = group_H2O(1)
            branch 1, index 0: "group_H2O"    composition_formula = H2O(3)
            branch 2, index 0: "H2O"          composition_formula = H(1)O(2)
        """,
    )

    total_charge = Quantity(
        type=np.int32,
        description="""
        Total charge of the system.
        """,
    )

    total_spin = Quantity(
        type=np.int32,
        description="""
        Total spin quantum number **S** of the system (so Ŝ² ψ = S(S+1) ħ² ψ).
        Stored as an integer or half-integer represented in doubled form
        (e.g. singlet → 0, doublet → 1, triplet → 2).
        Not to be confused with the spin multiplicity 2S+1.
        """,
    )

    particle_states = SubSection(
        section_def=ParticleState.m_def,
        repeats=True,
        description="""
        Particle state of each of the particles conforming the ModelSystem.
        This is a list of `n_particles` elements and the order matches that of `positions`.

            Example
            -------
            A water molecule (H₂O):

                positions       : [[…], […], […]]      # 3 atoms
                particle_states :
                    [0] AtomsState(H)
                    [1] AtomsState(H)
                    [2] AtomsState(O)
        """,
    )

    sub_systems = SubSection(sub_section=SectionProxy('ModelSystem'), repeats=True)

    def __init__(self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        self.__is_atomic_flag = None

    @property
    def _is_atomic(self) -> bool:
        """
        If explicitly set (True/False), use that.
        Otherwise compute from current particle_states every time (no caching),
        so it can’t go stale.
        """
        if self.__is_atomic_flag is not None:
            return self.__is_atomic_flag
        return bool(self.particle_states) and all(
            isinstance(p, AtomsState) for p in self.particle_states
        )

    @_is_atomic.setter
    def _is_atomic(self, value: Optional[bool]) -> None:
        """
        Set to True/False to force; set to None to clear the override.
        """
        self.__is_atomic_flag = None if value is None else bool(value)

    def is_atomic(self) -> bool:
        return self._is_atomic

    # ? Is it better to get symbols with logging or make a property without?
    @log
    def get_symbols(self) -> list[str]:
        """
        Gets the symbols from the particle_states.
        Args:
            logger (BoundLogger): The logger to log messages.
        Returns:
            list: The list of symbols of the particles.
        """
        logger = self.get_symbols.__annotations__['logger']
        symbols = []
        for particle_state in self.particle_states:
            symbol = None
            if isinstance(particle_state, AtomsState):
                symbol = particle_state.chemical_symbol
            elif isinstance(particle_state, CGBeadState):
                symbol = particle_state.bead_symbol
            else:
                symbol = particle_state.label
            if not symbol:
                logger.warning('missing symbol in ParticleState.')
                return []
            symbols.append(symbol)
        return symbols

    def _all_labels_are_elements(self, labels: list[str]) -> bool:
        """True if every label is a valid element symbol."""
        if not labels:
            return False
        try:
            symbols2numbers(labels)
            return True
        except KeyError:
            return False

    @log
    def are_valid_chemical_symbols(self) -> bool:
        """
        Validate that ASE can map all element symbols in the particle_states
        to atomic numbers.
        Args:
            logger (BoundLogger): The logger to log messages.
        Returns:
            bool: True if all chemical symbols are valid, False otherwise.
        """
        logger = self.are_valid_chemical_symbols.__annotations__['logger']
        symbols = self.get_symbols(logger=logger)
        if not symbols:
            return False

        if self._all_labels_are_elements(symbols):
            return True

        logger.error('Invalid or missing chemical symbols.')
        return False

    @log
    def to_ase_atoms(self) -> 'Optional[ase.Atoms]':
        """
        Generates an ASE Atoms object from ModelSystem data.
        Uses:
          - atom_states to obtain chemical symbols,
          - positions from the top-level positions quantity,
          - periodic boundary conditions and lattice vectors from the first cell.
        """
        logger = self.to_ase_atoms.__annotations__['logger']
        symbols = self.get_symbols(logger=logger)
        if not symbols:
            logger.error('Cannot generate ASE Atoms without chemical symbols.')
            return None

        ase_atoms = ase.Atoms(symbols=symbols)

        # Use cell data for periodic boundary conditions and lattice
        if self.cell:
            cell_section = self.cell
            if cell_section.periodic_boundary_conditions is None:
                logger.info(
                    'Cell periodic_boundary_conditions not found; using default [False, False, False].'
                )
                pbc = [False, False, False]
            else:
                pbc = cell_section.periodic_boundary_conditions
            ase_atoms.set_pbc(pbc=pbc)

            if cell_section.lattice_vectors is not None:
                ase_atoms.set_cell(
                    cell_section.lattice_vectors.to('angstrom').magnitude
                )
            else:
                logger.info('No lattice_vectors found in cell.')
        else:
            logger.warning('No cell section available in ModelSystem.')

        # Check that positions have been set on the ModelSystem
        if self.positions is None:
            logger.error('ModelSystem.positions is not defined.')
            return None
        else:
            ase_atoms.set_positions(self.positions.to('angstrom').magnitude)
        return ase_atoms

    @log
    def from_ase_atoms(self, ase_atoms: ase.Atoms) -> None:
        """
        Populates ModelSystem from an ASE Atoms object.
        Replaces the atom_states subsection with new entries based on the ASE chemical symbols,
        and assigns ASE positions to the top-level positions quantity.
        """
        # ? Should particle_states be cleared before populating?
        # ? self._clear_particle_states_inplace()
        # Iterate over chemical symbols and atomic numbers from the ASE Atoms object
        logger = self.from_ase_atoms.__annotations__['logger']
        for symbol, atomic_number in zip(
            ase_atoms.get_chemical_symbols(), ase_atoms.get_atomic_numbers()
        ):
            state = AtomsState(chemical_symbol=symbol, atomic_number=atomic_number)
            self.particle_states.append(state)

        positions = ase_atoms.get_positions()
        if not positions.tolist():
            logger.error('ASE Atoms has no positions.')
            return
        self.positions = positions * ureg('angstrom')
        self.n_particles = len(self.positions)

        # Update cell information from ASE
        if self.cell:
            cell = ase_atoms.get_cell()
            self.cell.lattice_vectors = ase.geometry.complete_cell(cell) * ureg(
                'angstrom'
            )
            self.cell.periodic_boundary_conditions = ase_atoms.get_pbc()

    def resolve_system_type_and_dimensionality(
        self, ase_atoms: ase.Atoms, logger: 'BoundLogger'
    ) -> tuple[str, int]:
        """
        Resolves the `ModelSystem.type` and `ModelSystem.dimensionality` using `MatID` classification analyzer:

            - https://singroup.github.io/matid/tutorials/classification.html

        Args:
            ase.Atoms: The ASE Atoms structure to analyse.
        Returns:
            system_type, dimensionality (tuple[str]): The system type and dimensionality as determined by MatID.
        """
        classification = None
        system_type, dimensionality = self.type, self.dimensionality
        if len(ase_atoms) <= configuration.limit_system_type_classification:
            try:
                classifier = Classifier(
                    radii='covalent',
                    cluster_threshold=configuration.cluster_threshold,
                )
                classification = classifier.classify(input_system=ase_atoms)
            except Exception as e:
                logger.warning(
                    'MatID system classification failed.', exc_info=e, error=str(e)
                )
                return system_type, dimensionality

            if isinstance(classification, Class3D):
                system_type = 'bulk'
                dimensionality = 3
            elif isinstance(classification, Atom):
                system_type = 'atom'
                dimensionality = 0
            elif isinstance(classification, Class0D):
                system_type = 'molecule / cluster'
                dimensionality = 0
            elif isinstance(classification, Class1D):
                system_type = '1D'
                dimensionality = 1
            elif isinstance(classification, Surface):
                system_type = 'surface'
                dimensionality = 2
            elif isinstance(classification, (Class2D, Material2D)):
                system_type = '2D'
                dimensionality = 2
        else:
            logger.info(
                'ModelSystem.type and dimensionality analysis not run due to large system size.'
            )

        return system_type, dimensionality

    # ! Needs to be checked !
    def _copy_common_quantities(self, src, dst, *, exclude: set[str] = None) -> None:
        exclude = exclude or set()

        def _qnames(section) -> set[str]:
            aq = getattr(section.m_def, 'all_quantities', None)
            if aq is None:
                return set()
            if isinstance(aq, dict):
                return set(aq.keys())
            # iterable of Quantity objects
            return {q.name for q in aq}

        src_q = _qnames(src)
        dst_q = _qnames(dst)
        for name in (src_q & dst_q) - exclude:
            val = getattr(src, name, None)
            if val is not None:
                setattr(dst, name, val)

    def _clear_particle_states_inplace(self) -> None:
        while len(self.particle_states):
            self.particle_states.pop()

    def _reassign_generic_particle_states(self, archive, logger) -> None:
        """
        If the parser populated only generic ParticleState entries, convert *all* to:
        - AtomsState if all labels are valid element symbols, else
        - CGBeadState.
        If any AtomsState/CGBeadState is already present, do nothing (trust parser).
        """
        if not self.particle_states:
            return

        ps_list = list(self.particle_states)

        # Only act if *every* entry is plain ParticleState (no AA/CG mixed in)
        if not all(
            isinstance(p, ParticleState)
            and not isinstance(p, (AtomsState, CGBeadState))
            for p in ps_list
        ):
            return

        labels = self.get_symbols(logger=logger)
        to_atoms = bool(labels) and self._all_labels_are_elements(labels)

        self._clear_particle_states_inplace()

        if to_atoms:
            # Map one-to-one using validated element labels
            for old, lab in zip(ps_list, labels):
                new = AtomsState()
                new.chemical_symbol = lab  # validated by symbols2numbers + MEnum on set
                # Copy all overlapping fields EXCEPT chemical_symbol (we just set it)
                self._copy_common_quantities(old, new, exclude={'chemical_symbol'})
                new.normalize(archive, logger)
                self.particle_states.append(new)
            self._is_atomic = True
        else:
            # Fall back to CG; use each original ParticleState.label (may be None)
            for old in ps_list:
                lab = getattr(old, 'label', None)
                new = CGBeadState()
                if lab:
                    new.bead_symbol = lab
                # Copy all overlapping fields EXCEPT bead_symbol (we just set it)
                self._copy_common_quantities(old, new, exclude={'bead_symbol'})
                new.normalize(archive, logger)
                self.particle_states.append(new)
            self._is_atomic = False

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # reassign particle states according to label validity
        self._reassign_generic_particle_states(archive, logger)

        # We don't need to normalize if the system is not representative
        # TODO decide the meaning and exact usage of a system being representative
        # TODO before avoiding normalization
        # if is_not_representative(model_system=self, logger=logger):
        #     return

        ## ATOMIC NORMALIZATION
        if not self._is_atomic:
            return
        # Generate ASE Atoms object from top-level ModelSystem data
        ase_atoms = self.to_ase_atoms(logger=logger)
        if ase_atoms is None:
            logger.error('Could not generate ASE Atoms from ModelSystem.')
            return

        # Resolve system type and dimensionality using ASE atoms
        self.type, self.dimensionality = self.resolve_system_type_and_dimensionality(
            ase_atoms, logger
        )

        # Create and normalize Symmetry section if applicable
        if self.type == 'bulk' and self.symmetry is None:
            sec_symmetry = GlobalCrystalSymmetry()
            self.symmetry = sec_symmetry
            sec_symmetry.normalize(archive, logger)

        # Create and normalize ChemicalFormula section
        sec_chemical_formula = ChemicalFormula()
        sec_chemical_formula.normalize(archive, logger)
        if sec_chemical_formula.m_cache:
            self.elemental_composition = sec_chemical_formula.m_cache.get(
                'elemental_composition', []
            )

    def _generate_comparer(self):
        if self.positions is None:
            return []
        # Create a list of HashedPositions for each atom's coordinates
        return [HashedPositions(pos) for pos in self.positions]

    def is_equal_structure(self, other: 'ModelSystem') -> bool:
        return set(self._generate_comparer()) == set(other._generate_comparer())

    def is_lt_structure(self, other: 'ModelSystem') -> bool:
        return set(self._generate_comparer()) < set(other._generate_comparer())

    def is_le_structure(self, other: 'ModelSystem') -> bool:
        return set(self._generate_comparer()) <= set(other._generate_comparer())

    def is_gt_structure(self, other: 'ModelSystem') -> bool:
        return set(self._generate_comparer()) > set(other._generate_comparer())

    def is_ge_structure(self, other: 'ModelSystem') -> bool:
        return set(self._generate_comparer()) >= set(other._generate_comparer())

    def is_ne_structure(self, other: 'ModelSystem') -> bool:
        return not self.is_equal_structure(other)

    # functions for traversing the ModelSystem hierarchy
    def get_root_system(self) -> 'ModelSystem':
        """
        Traverses up the hierarchy to find the root ModelSystem.

        Returns:
            ModelSystem: The top-level (root) ModelSystem.
        """
        system = self
        while isinstance(system.m_parent, ModelSystem):
            system = system.m_parent
        return system

    # functions for working with molecules
    def get_bond_list(self, set_local: bool = False) -> np.ndarray:
        """
        Retrieves the bond list for this subsystem by filtering the root bond_list
        using the subsystem's `particle_indices`. The bond indices remain in root-level
        coordinates (no reindexing).

        Args:
            set_local (bool): If True, sets `self.bond_list` to the filtered bonds.

        Returns:
            np.ndarray: Filtered bond list for this subsystem (root-level indices).
        """

        if not isinstance(self.m_parent, ModelSystem):  # this is the root system
            return self.bond_list

        if self.particle_indices is None:
            return np.array([])

        root = self.get_root_system()
        if root.bond_list is None:
            return np.array([])

        indices_set = set(self.particle_indices.tolist())
        bond_list = np.array(
            [
                (i, j)
                for i, j in root.bond_list
                if i in indices_set and j in indices_set
            ],
            dtype=np.int32,
        )

        if set_local:
            self.bond_list = bond_list

        return bond_list

    def is_molecule(self) -> bool:
        """
        Checks if the current subsystem forms a contiguous and isolated molecule:
        - All particles are connected (single connected component).
        - No bonds connect particles inside this subsystem to particles outside it.

        Returns:
            bool: True if the subsystem is an isolated molecule, False otherwise.
        """
        import networkx as nx

        # Internal bonds for this subsystem
        bonds = self.get_bond_list(set_local=False)

        # Handle case: no bonds
        if bonds.size == 0:
            return False

        # Determine particle indices (fallback to range if None)
        particle_indices = self.particle_indices
        if particle_indices is None:
            n_particles = (
                len(self.positions) if self.positions is not None else self.n_particles
            )
            particle_indices = np.arange(n_particles, dtype=np.int32)

        # --- 1. Connectivity check ---
        graph = nx.Graph()
        graph.add_nodes_from(particle_indices)
        graph.add_edges_from(bonds)

        if not nx.is_connected(graph):
            return False

        # --- 2. Isolation check: ensure no bonds cross subsystem boundary ---
        root = self.get_root_system()
        if root.bond_list is not None:
            indices_set = set(particle_indices.tolist())
            for i, j in root.bond_list:
                # If exactly one endpoint is inside → cross-boundary bond
                if (i in indices_set) ^ (j in indices_set):
                    return False

        return True
