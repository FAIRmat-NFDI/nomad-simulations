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
from hashlib import sha1
from typing import TYPE_CHECKING

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
from nomad.datamodel.context import Context
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.basesections.v2 import System
from nomad.metainfo import MEnum, Quantity, SectionProxy, SubSection
from nomad.metainfo.metainfo import Section
from nomad.units import ureg

from nomad_simulations.schema_packages.utils import log

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    import pint
    from nomad.datamodel.context import Context
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    CGBeadState,
    ElectronicState,
    ParticleState,
)

configuration = config.get_plugin_entry_point(
    'nomad_simulations.schema_packages:nomad_simulations_plugin'
)


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


class Representation(ArchiveSection):
    """
    A comprehensive section containing all representation information of a system, including
    lattice vectors, periodic boundary conditions, positions, and symmetry-related data.

    This class unifies properties from:
    - GeometricSpace: geometric properties like vectors lengths, angles, volumes, coordinate systems
    - Cell: lattice vectors, periodic boundary conditions, supercell information
    - Structural data: atomic positions (Cartesian and fractional), Wyckoff positions, equivalent atoms

    This design allows for multiple representations of the same system (e.g., primitive,
    conventional, supercell) to coexist while maintaining a consistent interface.

    See the [Representation Architecture](https://nomad-lab.eu/prod/v1/staging/docs/howto/customization/plugins_dev.html)
    documentation for detailed information about the design philosophy and usage patterns.
    """

    name = Quantity(
        type=str,
        description="""
        Name of the specific representation. This can be used for easy identification.
        """,
    )

    coordinates_system = Quantity(
        type=MEnum('cartesian', 'cylindrical', 'spherical', 'ellipsoidal', 'polar'),
        default='cartesian',
        description="""
        Coordinate system convention used to interpret the positions quantity. Defaults to 'cartesian',
        which is used in practice for almost all simulation data.

        For 'cartesian', positions and lattice_vectors are expressed in an implicit Cartesian frame (x, y, z).

        | name       | description | dimensionalities | coordinates |
        |------------|-------------|------------------|-------------|
        | cartesian  | implicit Cartesian coordinate system | 1, 2, 3 | x, y, z |
        | cylindrical| cylindrical symmetry | 3 | r, theta, z |
        | spherical  | spherical symmetry | 3 | r, theta, phi |
        | ellipsoidal| spherically elongated system | 3 | r, theta, phi |
        | polar      | spherical symmetry | 2 | r, theta |
        """,
    )  # ? in practice we use cartesian only...

    # TODO: in the future, we may need to disambiguate between "basis vectors of the reference frame" and "lattice vectors"
    # in cases where the terminology could be confusing. The lattice vectors define the periodic cell,
    # while the reference frame basis vectors (x, y, z) are implicit and not stored.
    lattice_vectors = Quantity(
        type=np.float64,
        shape=[3, 3],
        unit='meter',
        description="""
        Lattice vectors of the simulated cell, stored as a 3x3 matrix where each row is a lattice vector.
        The first index runs over each lattice vector (a, b, c). The second index runs over the
        implicit Cartesian coordinate system (x, y, z), the same frame used for positions.
        """,
    )

    periodic_boundary_conditions = Quantity(
        type=bool,
        shape=[3],
        description="""
        Denotes whether periodic boundary conditions are applied. Runs over each axis.
        Requires `lattice_vectors` to be defined, else it is left empty.
        """,
    )

    volume = Quantity(
        type=np.float64,
        unit='meter ** 3',
        description="""
        Volume of a 3D real space entity.
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

    boundary_area = Quantity(
        type=np.float64,
        unit='meter ** 2',
        description="""
        Surface area of a 3D real space entity.
        """,
    )

    boundary_length = Quantity(
        type=np.float64,
        unit='meter',
        description="""
        Length of the boundary of a 2D real space entity.
        """,
    )

    fractional_coordinates = (
        Quantity(  # TODO rename to fractional_positions for consistency
            type=np.float64,
            shape=['*', 3],
            description="""
            Fractional coordinates of all atoms in the system with respect to the lattice vectors.
            Values typically range from 0 to 1 within the unit cell, though atoms may lie outside
            this range in non-periodic directions or due to wrapping conventions.
        """,
        )
    )

    local_symmetry = SubSection(sub_section='LocalSymmetry')


class AlternativeRepresentation(Representation):
    """
    A representation relative to another, reference representation, typically the original computed system.
    """

    # Mimics spglib's dataset['origin_shift'] from get_symmetry_dataset()
    origin_shift = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Translation vector relating the origin of this representation to the reference representation,
        expressed in fractional coordinates. Together with transformation_matrix, defines how fractional
        coordinates transform between representations: x_alt = P @ x_ref + p, where both representations
        use the same implicit Cartesian frame but different lattice vectors. Commonly used to relate
        input cells to standardized conventional cells in symmetry analysis (e.g., from [spglib](https://spglib.readthedocs.io/en/latest/definition.html)).
        """,
    )

    # Mimics spglib's dataset['transformation_matrix'] from get_symmetry_dataset()
    transformation_matrix = Quantity(
        type=np.float64,
        shape=[3, 3],
        description="""
        Transformation matrix P relating lattice vectors between this representation and the reference
        representation. Lattice vectors transform as: (a_alt, b_alt, c_alt) = (a_ref, b_ref, c_ref) @ P^-1.
        Together with origin_shift, defines how fractional coordinates transform: x_alt = P @ x_ref + p.
        Both representations use the same implicit Cartesian frame; this matrix only changes how fractional
        coordinates are expressed relative to different lattice vectors. Commonly used in symmetry analysis
        to relate input cells to standardized conventional cells (e.g., from [spglib](https://spglib.readthedocs.io/en/latest/definition.html)).
        """,
    )

    crystal_cell_type = Quantity(
        type=MEnum('primitive', 'conventional'),
        description="""
        Representation type of the cell structure. It might be:
            - 'primitive' as the primitive unit cell,
            - 'conventional' as the conventional cell used for referencing.
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


class LocalSymmetry(ArchiveSection):
    """
    Base class for per-particle local symmetry information.

    Provides polymorphic interface for different types of local symmetry data.
    Each representation can have its own LocalSymmetry since particle counts differ.
    """

    equivalent_atoms = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        Equivalence grouping of atoms by symmetry operations.
        Atoms with the same index value are symmetrically equivalent.

        Examples:
            - [0, 1, 2, 3]: all four atoms are non-equivalent
            - [0, 0, 0, 3]: first three atoms are equivalent, fourth is unique
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Validate array dimensions match parent representation particle count."""
        super().normalize(archive, logger)

        parent = self.m_parent
        if not isinstance(parent, Representation):
            logger.warning(
                'LocalSymmetry parent is not a Representation → validation skipped.'
            )
            return

        # Validate array lengths against parent representation
        if (
            hasattr(parent, 'fractional_coordinates')
            and parent.fractional_coordinates is not None
        ):
            n_particles = len(parent.fractional_coordinates)

            # Check each populated array for any quantity with shape ['*']
            for field_name, quantity in self.m_def.all_quantities.items():
                if quantity.shape and quantity.shape[0] == '*':
                    field_value = getattr(self, field_name, None)
                    if field_value is not None and len(field_value) != n_particles:
                        logger.warning(
                            f'{self.__class__.__name__}.{field_name} length ({len(field_value)}) '
                            f'does not match n_particles ({n_particles})'
                        )


class LocalCrystalSymmetry(LocalSymmetry):
    """
    Crystallographic local symmetry for particles in a crystal structure.

    Stores Wyckoff positions, site symmetries, and multiplicities for each particle
    in the representation.
    """

    site_symmetries = Quantity(
        type=str,
        shape=['*'],
        description="""
        Crystallographic point group symbol for each particle site in Hermann-Mauguin notation.

        Each symbol (e.g., '3m', 'mmm', '432', '1') describes the local symmetry operations
        that leave the atomic site invariant within the crystal structure. These are the
        site symmetry groups—subgroups of the full space group that preserve the specific
        atomic position.

        The site symmetry is intrinsically linked to the Wyckoff position: atoms at the same
        Wyckoff position share the same site symmetry, though the converse is not always true.
        Higher symmetry positions (lower Wyckoff letters like 'a') typically have higher-order
        site symmetries.

        **Source**: Determined via spglib symmetry analysis (accessed through MatID), which
        uses the geometric positions of atoms to identify symmetry operations.

        Examples:
        - '1' - No symmetry (general position)
        - '3m' - Threefold rotation with mirror plane
        - 'mmm' - Three perpendicular mirror planes (orthorhombic)
        - '-43m' - Cubic tetrahedral symmetry
        """,
    )

    wyckoff_letters = Quantity(
        type=str,
        shape=['*'],
        description="""
        Wyckoff letter designation for each atomic position in this representation.

        Wyckoff positions are the crystallographically distinct positions in a space group, as defined in the
        **International Tables for Crystallography** and accessible through resources like the **Bilbao
        Crystallographic Server** (https://www.cryst.ehu.es/) and the **International Union of Crystallography
        databases** (https://www.iucr.org/resources/data).

        The Wyckoff letter (a, b, c, ...) identifies positions in order of **decreasing site symmetry**, with
        `a` typically representing the **highest symmetry** (most special) position.

        **Important**:
        Wyckoff positions are determined using **geometric space group analysis** (via spglib/MatID),
        which considers **only atomic positions** and ignores chemical species.
        This means atoms of different elements may share the same Wyckoff designation
        if they occupy geometrically equivalent positions.
        For complete crystallographic uniqueness, combine `wyckoff_letters` with chemical information.

        Use the `wyckoff_sites` property to get the combined letter+multiplicity format (e.g., "a1", "b2").

        References:
        - International Tables for Crystallography, Volume A: Space-group symmetry
        - Aroyo, M.I. et al. (2006). "Bilbao Crystallographic Server." Z. Kristallogr. 221, 15-27
        - Aroyo, M.I. et al. (2011). "Crystallography online: Bilbao Crystallographic Server."
          Bulg. Chem. Commun. 43, 183-197
        """,
    )

    site_multiplicities = Quantity(
        type=np.int32,
        shape=['*'],
        description="""
        Multiplicity of the Wyckoff site for each particle.

        The **multiplicity** indicates how many symmetrically equivalent positions are generated by
        applying all space group operations to this Wyckoff site within the **conventional unit cell**.

        For example:
        - Multiplicity 1: Special position with highest symmetry (unique in the unit cell)
        - Multiplicity 2, 4, 8, etc.: Positions with lower symmetry that appear multiple times

        Note: The multiplicity is determined from the conventional cell. In primitive cells or supercells,
        fewer or more atoms of this type may be present, but the multiplicity value remains the same
        as it's an intrinsic property of the Wyckoff position.
        """,
    )

    @property
    def wyckoff_sites(self) -> list[str] | None:
        """
        Wyckoff site designation formatted as `<letter><multiplicity>` (e.g., `a1`, `b2`).

        This property combines `wyckoff_letters` and `site_multiplicities` into a convenient
        single format matching the notation commonly used in crystallography literature.

        Returns:
            list[str] | None: List of Wyckoff site annotations in format "letter+multiplicity",
            or None if either wyckoff_letters or site_multiplicities is not set.

        Examples:
            - ['a1', 'b2', 'b2', 'c4', 'c4', 'c4', 'c4'] indicates:
              • 1 atom at Wyckoff position 'a' (special position, multiplicity 1)
              • 2 symmetrically equivalent atoms at Wyckoff position 'b' (multiplicity 2)
              • 4 symmetrically equivalent atoms at Wyckoff position 'c' (multiplicity 4)
        """
        if self.wyckoff_letters is None or self.site_multiplicities is None:
            return None
        if len(self.wyckoff_letters) != len(self.site_multiplicities):
            return None
        return [
            f'{letter}{mult}'
            for letter, mult in zip(self.wyckoff_letters, self.site_multiplicities)
        ]


class GlobalSymmetry(ArchiveSection):
    """
    A base section specifying the global symmetry of the corresponding `ModelSystem` at large,
    which can be used for categorization and lookup. It does not define local, site-specific symmetry.
    """


class GlobalCrystalSymmetry(GlobalSymmetry):
    """
    A symmetry section specialized for identifying bulk crystal space groups.

    This section stores crystallographic symmetry information extracted from the atomic structure,
    including space group identifiers, Bravais lattice type, and structural prototype classifications.

    Note: this information can be extracted via normalization using the MatID package, if `ModelSystem`
    is specified.
    """

    lattice_type = Quantity(
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
        Bravais lattice type (crystal family classification).

        The first lowercase letter of Pearson notation, identifying the crystal family
        based on lattice symmetry:

        **3D lattices:**
        - a: triclinic
        - m: monoclinic
        - o: orthorhombic
        - t: tetragonal
        - r: trigonal
        - h: hexagonal
        - c: cubic

        **2D lattices:**
        - mp: oblique
        - op: rectangular
        - oc: centered rectangular
        - tp: square
        - hp: hexagonal 2D

        **1D lattices:**
        - ap: linear

        This quantity enables independent querying of crystal families
        (e.g., "all cubic systems" regardless of centering type).
        """,
    )

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
        Lattice centering type.

        The second uppercase letter of Pearson notation, describing how lattice points
        are distributed within the conventional unit cell:

        **3D centerings:**
        - P: primitive (lattice points only at cell corners)
        - R: rhombohedral (hexagonal setting with 2/3, 1/3 centering)
        - S: face centered (one pair of opposite faces centered)
        - I: body centered (center of cell)
        - F: all faces centered (all faces have centered points)

        **2D centerings:**
        - c: centered rectangular
        - p: primitive 2D

        **1D centerings:**
        - p: primitive 1D

        This quantity enables independent querying of centering types
        (e.g., "all face-centered lattices" regardless of crystal family).
        """,
    )

    hall_symbol = Quantity(
        type=str,
        description="""
        Hall symbol for this system describing the minimum number of symmetry operations
        needed to uniquely define a space group. See https://cci.lbl.gov/sginfo/hall_symbols.html.
        Examples:
            - `F -4 2 3`,
            - `-P 4 2`,
            - `-F 4 2 3`.
        """,
    )

    hall_number = Quantity(
        type=np.int32,
        description="""
        Hall number uniquely identifying the Hall symbol. This is an integer from 1 to 530
        for 3D space groups, providing a numerical index into the Hall symbol table.
        Different settings or origin choices of the same space group have different Hall numbers.
        """,
    )

    point_group_symbol = Quantity(
        type=str,
        description="""
        Symbol of the crystallographic point group in the Hermann-Mauguin notation. See
        https://en.wikipedia.org/wiki/Crystallographic_point_group. Examples:
            - `-43m`,
            - `4/mmm`,
            - `m-3m`.
        """,
    )

    space_group_number = Quantity(
        type=np.int32,
        description="""
        Specifies the International Union of Crystallography (IUC) space group number of the 3D
        space group of this system. See https://en.wikipedia.org/wiki/List_of_space_groups.
        Examples:
            - `216`,
            - `123`,
            - `225`.
        """,
    )

    space_group_symbol = Quantity(
        type=str,
        description="""
        Specifies the International Union of Crystallography (IUC) space group symbol of the 3D
        space group of this system. See https://en.wikipedia.org/wiki/List_of_space_groups.
        Examples:
            - `F-43m`,
            - `P4/mmm`,
            - `Fm-3m`.
        """,
    )

    strukturbericht_designation = Quantity(
        type=str,
        description="""
        Classification of the material according to the historically grown and similar crystal
        structures ('strukturbericht'). Useful when using altogether with `space_group_symbol`.
        Examples:
            - `C1B`, `B3`, `C15b`,
            - `L10`, `L60`,
            - `L21`.

        Extracted from the AFLOW encyclopedia of crystallographic prototypes.
        """,
    )

    prototype_formula = Quantity(
        type=str,
        description="""
        The formula of the prototypical material for this structure as extracted from the
        AFLOW encyclopedia of crystallographic prototypes. It is a string with the chemical
        symbols:
            - https://aflowlib.org/prototype-encyclopedia/chemical_symbols.html
        """,
    )

    prototype_aflow_id = Quantity(
        type=str,
        description="""
        The identifier of this structure in the AFLOW encyclopedia of crystallographic prototypes:
            http://www.aflowlib.org/prototype-encyclopedia/index.html
        """,
    )

    analysis_origin_shift = Quantity(
        type=np.float64,
        shape=[3],
        description="""
        Origin shift vector (3-element) applied by spglib during symmetry standardization.

        This vector describes the shift from the standardized origin to the input structure's
        origin in fractional coordinates. During symmetry analysis, spglib may shift the origin
        to align with conventional crystallographic settings (e.g., placing inversion centers
        or high-symmetry points at the origin).

        The shift is applied as: **r_input = r_standardized + origin_shift**

        where r_input is a position in the input structure and r_standardized is the
        corresponding position in the standardized cell.

        **Source**: Extracted from spglib's symmetry dataset via MatID's `SymmetryAnalyzer`.

        **Note**: This transformation is specific to the symmetry analysis process and is
        distinct from user-defined representation transformations.

        See: https://spglib.readthedocs.io/en/stable/definition.html
        """,
    )

    analysis_transformation_matrix = Quantity(
        type=np.float64,
        shape=[3, 3],
        description="""
        Transformation matrix (3×3) from input lattice vectors to standardized lattice vectors.

        This matrix describes how spglib transforms the input unit cell into a standardized
        conventional cell during symmetry analysis. The transformation is defined such that:

        **L_input = L_standardized @ transformation_matrix**

        where L_input is the matrix of input lattice vectors (as columns) and L_standardized
        is the matrix of standardized lattice vectors.

        The standardization process orients the cell according to conventional crystallographic
        settings for the identified space group, which may involve:
        - Reorienting axes to align with symmetry elements
        - Converting between primitive and conventional cells
        - Standardizing the choice of basis vectors

        **Source**: Extracted from spglib's symmetry dataset via MatID's `SymmetryAnalyzer`.

        **Note**: This is specifically the transformation applied during symmetry detection
        and is distinct from user-defined representation transformations.

        See: https://spglib.readthedocs.io/en/stable/definition.html
        """,
    )

    atomic_cell_ref = Quantity(
        type=Representation,
        description="""
        **DEPRECATED**: This field is deprecated and will be removed in a future version.

        Originally intended to reference the representation that symmetry describes, but this
        design was flawed: symmetry analysis is performed on the original ModelSystem structure
        (representation-independent), not on a specific representation. The primitive and
        conventional cells are outputs of symmetry analysis, not inputs.

        The field currently points to the conventional cell (an output), which is semantically
        incorrect and provides no useful information beyond what's already in
        `model_system.representations`.

        **Migration**: No action needed. This field provides no functionality and can be ignored.
        """,
    )

    def _parse_bravais_lattice_pearson(
        self, pearson: str, logger: 'BoundLogger'
    ) -> tuple[str | None, str | None]:
        """
        Parse a Pearson notation string into lattice_type and lattice_centering components.

        Pearson notation is a two-letter code where:
        - First letter indicates crystal family (a, m, o, t, r, h, c for 3D; mp, op, oc, tp, hp, ap for 2D/1D)
        - Second letter indicates centering (P, I, F, S, R for 3D; p, c for 2D)

        Args:
            pearson (str): Pearson notation string (e.g., "cF" for cubic face-centered).
            logger (BoundLogger): The logger to log messages.

        Returns:
            tuple[str | None, str | None]: A tuple of (lattice_type, lattice_centering) MEnum values,
            or (None, None) if parsing fails.
        """
        if not pearson or len(pearson) < 2:
            logger.warning(f'Invalid Pearson notation: {pearson}')
            return None, None

        # Mapping from Pearson first character to lattice_type MEnum
        family_map = {
            'a': 'a - triclinic',
            'm': 'm - monoclinic',
            'o': 'o - orthorhombic',
            't': 't - tetragonal',
            'r': 'r - trigonal',
            'h': 'h - hexagonal',
            'c': 'c - cubic',
            'mp': 'mp - oblique',
            'op': 'op - rectangular',
            'oc': 'oc - centered rectangular',
            'tp': 'tp - square',
            'hp': 'hp - hexagonal 2D',
            'ap': 'ap - linear',
        }

        # Mapping from Pearson second character to lattice_centering MEnum
        centering_map = {
            'P': 'P - primitive',
            'I': 'I - body centred',
            'F': 'F - all faces centred',
            'S': 'S - face centred',
            'R': 'R - rhombohedral',
            'c': 'c - centered 2D',
            'p': 'p - primitive 2D/1D',
        }

        # Extract family and centering from Pearson notation
        family_code = pearson[0].lower()
        centering_code = pearson[1] if len(pearson) > 1 else ''

        lattice_type = family_map.get(family_code)
        lattice_centering = centering_map.get(centering_code)

        if not lattice_type:
            logger.warning(f'Unknown crystal family in Pearson notation: {family_code}')
        if not lattice_centering:
            logger.warning(f'Unknown centering in Pearson notation: {centering_code}')

        return lattice_type, lattice_centering

    @property
    def bravais_lattice(self) -> str | None:
        """
        Reconstructs the Pearson notation from lattice_type and lattice_centering.

        This property provides backward compatibility for code that expects the combined
        Pearson notation string (e.g., "cF" for cubic face-centered).

        Returns:
            str | None: Pearson notation string, or None if components are not set.
        """
        if not self.lattice_type or not self.lattice_centering:
            return None

        # Extract the letter codes from the MEnum values
        # MEnum format is "X - description", we need just the first character(s)
        family_code = self.lattice_type.split(' - ')[0] if self.lattice_type else ''
        centering_code = (
            self.lattice_centering.split(' - ')[0] if self.lattice_centering else ''
        )

        return (
            f'{family_code}{centering_code}' if family_code and centering_code else None
        )

    @staticmethod
    def _compute_site_multiplicities(
        equivalent_atoms: 'np.ndarray | list',
    ) -> list[int]:
        """
        Compute site multiplicities from equivalent_atoms grouping.

        For each atom, the multiplicity is the number of atoms that share the same
        equivalent_atoms index (i.e., atoms related by space group symmetry operations).

        This method correctly handles parametric Wyckoff positions where the same
        Wyckoff letter can appear at different coordinate parameters, creating
        distinct non-equivalent sites.

        Args:
            equivalent_atoms: Array mapping each atom to its independent atom index.
                Atoms with the same index are symmetrically equivalent.

        Returns:
            List of site multiplicities, one per atom.

        Examples:
            >>> _compute_site_multiplicities([0, 0, 2, 2])
            [2, 2, 2, 2]  # Two pairs of equivalent atoms

            >>> _compute_site_multiplicities([0, 0, 0, 0, 4, 4])
            [4, 4, 4, 4, 2, 2]  # Four equivalent + two equivalent
        """
        # Convert to list for consistent counting behavior
        equiv_list = (
            list(equivalent_atoms)
            if hasattr(equivalent_atoms, '__iter__')
            else [equivalent_atoms]
        )
        # For each atom, count how many atoms share its equivalent_atoms index
        return [equiv_list.count(equiv_list[i]) for i in range(len(equiv_list))]

    def resolve_analyzed_cell(
        self,
        symmetry_analyzer: 'SymmetryAnalyzer',
        cell_type: str,
        logger: 'BoundLogger',
    ) -> 'Representation | None':
        """
        Resolves the `Representation` section from the `SymmetryAnalyzer` object and the cell_type
        (primitive or conventional).

        Args:
            symmetry_analyzer (SymmetryAnalyzer): The `SymmetryAnalyzer` object used to resolve.
            cell_type (str): The type of cell to resolve, either 'primitive' or 'conventional'.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[Representation]): The resolved `Representation` section or None if the cell_type
            is not recognized.
        """
        # Define a mapping for each supported cell type
        cell_type_map = {
            'primitive': {
                'wyckoff': symmetry_analyzer.get_wyckoff_letters_primitive,
                'equivalent': symmetry_analyzer.get_equivalent_atoms_primitive,
                'system': symmetry_analyzer.get_primitive_system,
            },
            'conventional': {
                'wyckoff': symmetry_analyzer.get_wyckoff_letters_conventional,
                'equivalent': symmetry_analyzer.get_equivalent_atoms_conventional,
                'system': symmetry_analyzer.get_conventional_system,
            },
        }

        mapping = cell_type_map.get(cell_type)
        if mapping is None:
            logger.error('Cell type %s is not supported.', cell_type)
            return None

        try:
            # We only need the system to extract cell information
            system = mapping['system']()
        except Exception as e:
            logger.error('Error extracting symmetry data', exc_info=e)
            return None

        cell = system.get_cell()

        # Create the representation with geometry
        cell_section = Representation()
        if cell_type is not None:
            cell_section.name = cell_type
        cell_section.lattice_vectors = cell * ureg.angstrom

        try:
            cell_section.volume = cell.volume * ureg.angstrom**3
        except Exception as exc:
            logger.warning(
                'Failed to extract geometric-space data from ASE cell.',
                exc_info=exc,
            )

        # Populate local symmetry information
        try:
            wyckoff = mapping['wyckoff']()
            equivalent = mapping['equivalent']()
            if wyckoff is not None or equivalent is not None:
                cell_section.local_symmetry = LocalCrystalSymmetry()
                if wyckoff is not None:
                    cell_section.local_symmetry.wyckoff_letters = wyckoff

                    # Compute site_multiplicities from equivalent_atoms grouping
                    if equivalent is not None:
                        site_mults = self._compute_site_multiplicities(equivalent)
                        cell_section.local_symmetry.site_multiplicities = site_mults

                if equivalent is not None:
                    cell_section.local_symmetry.equivalent_atoms = equivalent
        except Exception as exc:
            logger.warning(
                f'Failed to extract local symmetry for {cell_type} cell.',
                exc_info=exc,
            )

        return cell_section

    def resolve_bulk_symmetry(
        self, model_system: 'ModelSystem', logger: 'BoundLogger'
    ) -> 'tuple[Representation | None, Representation | None]':
        """
        Resolves the symmetry of the material being simulated using MatID and the
        originally parsed data under ModelSystem. It generates two other
        `Representation` sections (the primitive and standardized cells), as well as populating
        the `Symmetry` section and updating the ModelSystem with Wyckoff and equivalent atoms data.

        Args:
            model_system (ModelSystem): The `ModelSystem` section that the symmetry
            uses in MatID.SymmetryAnalyzer().
            logger (BoundLogger): The logger to log messages.
        Returns:
            primitive_cell, conventional_cell (tuple[Optional[Representation], Optional[Representation]]): The primitive and standardized `Representation` sections.
        """
        symmetry = {}
        try:
            ase_atoms = model_system.to_ase_atoms(
                representation_index=None, logger=logger
            )
            symmetry_analyzer = SymmetryAnalyzer(
                ase_atoms, symmetry_tol=configuration.symmetry_tolerance
            )
        except ValueError as e:
            logger.debug(
                'Symmetry analysis with MatID is not available.', details=str(e)
            )
            return None, None
        except Exception as e:
            logger.warning('Symmetry analysis with MatID failed.', exc_info=e)
            return None, None

        # We store symmetry_analyzer info in a dictionary
        bravais_pearson = symmetry_analyzer.get_bravais_lattice()
        if bravais_pearson:
            lattice_type, lattice_centering = self._parse_bravais_lattice_pearson(
                bravais_pearson, logger
            )
            symmetry['lattice_type'] = lattice_type
            symmetry['lattice_centering'] = lattice_centering

        symmetry['hall_symbol'] = symmetry_analyzer.get_hall_symbol()
        symmetry['hall_number'] = symmetry_analyzer.get_hall_number()
        symmetry['point_group_symbol'] = symmetry_analyzer.get_point_group()
        symmetry['space_group_number'] = symmetry_analyzer.get_space_group_number()
        symmetry['space_group_symbol'] = (
            symmetry_analyzer.get_space_group_international_short()
        )

        # Populate analysis_origin_shift, analysis_transformation_matrix, and
        # site_symmetries from the spglib dataset
        dataset = None
        try:
            dataset = symmetry_analyzer.get_symmetry_dataset()
            if dataset is not None:
                # Use attribute access (modern spglib API) with fallback to dict access
                symmetry['analysis_origin_shift'] = (
                    dataset.origin_shift
                    if hasattr(dataset, 'origin_shift')
                    else dataset.get('origin_shift')
                )
                symmetry['analysis_transformation_matrix'] = (
                    dataset.transformation_matrix
                    if hasattr(dataset, 'transformation_matrix')
                    else dataset.get('transformation_matrix')
                )
        except Exception as e:
            logger.warning(
                f'Could not extract analysis transformation data from symmetry dataset: {e}'
            )

        # Populating the ModelSystem local_symmetry information
        original_wyckoff = symmetry_analyzer.get_wyckoff_letters_original()
        original_equivalent_atoms = symmetry_analyzer.get_equivalent_atoms_original()

        if not model_system.local_symmetry:
            model_system.local_symmetry = LocalCrystalSymmetry()

        model_system.local_symmetry.wyckoff_letters = original_wyckoff
        model_system.local_symmetry.equivalent_atoms = original_equivalent_atoms

        # Compute site_multiplicities from equivalent_atoms grouping
        if original_equivalent_atoms is not None:
            site_mults = self._compute_site_multiplicities(original_equivalent_atoms)
            model_system.local_symmetry.site_multiplicities = site_mults

        # Populate site_symmetries (point group symbols) from symmetry dataset
        try:
            if dataset is not None:
                site_syms = (
                    dataset.site_symmetry_symbols
                    if hasattr(dataset, 'site_symmetry_symbols')
                    else dataset.get('site_symmetry_symbols')
                )
                if site_syms is not None:
                    # Convert to list and strip leading dots from symbols (e.g., '.3m' -> '3m')
                    # The dots are used by spglib but not standard in Hermann-Mauguin notation
                    model_system.local_symmetry.site_symmetries = [
                        sym.lstrip('.') if isinstance(sym, str) else sym
                        for sym in site_syms
                    ]
        except Exception as e:
            logger.warning(
                f'Could not extract site symmetry symbols from symmetry dataset: {e}'
            )

        # Populating the primitive Cell information
        primitive_cell = self.resolve_analyzed_cell(
            symmetry_analyzer=symmetry_analyzer, cell_type='primitive', logger=logger
        )

        # Populating the conventional Cell information
        conventional_cell = self.resolve_analyzed_cell(
            symmetry_analyzer=symmetry_analyzer, cell_type='conventional', logger=logger
        )

        # Getting prototype_formula, prototype_aflow_id, and strukturbericht designation from
        # standarized Wyckoff numbers and the space group number
        if symmetry.get('space_group_number') and conventional_cell is not None:
            # Retrieve the expanded conventional system (an ASE.Atoms object) from the analyzer.
            conventional_system = symmetry_analyzer.get_conventional_system()
            # Use the conventional system to get the expanded atomic numbers.
            conventional_num = conventional_system.get_atomic_numbers()
            # Get conventional wyckoff letters from the analyzer
            conventional_wyckoff = symmetry_analyzer.get_wyckoff_letters_conventional()
            norm_wyckoff = get_normalized_wyckoff(
                atomic_numbers=conventional_num, wyckoff_letters=conventional_wyckoff
            )
            aflow_prototype = search_aflow_prototype(
                space_group=symmetry.get('space_group_number'),
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
                symmetry['strukturbericht_designation'] = strukturbericht
                symmetry['prototype_aflow_id'] = prototype_aflow_id
                symmetry['prototype_formula'] = prototype_formula

        # Populating Symmetry section
        for key, val in self.m_def.all_quantities.items():
            self.m_set(val, symmetry.get(key))

        return primitive_cell, conventional_cell

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Get the parent ModelSystem
        model_system = self.m_parent
        if not isinstance(model_system, ModelSystem):
            logger.warning(
                'Parent is not a ModelSystem → symmetry normalization skipped.'
            )
            return

        # TODO : the following is a temporary fix, and it might break again
        # when there are systems with deeper hierarchies.
        if model_system.m_parent is not None and model_system.type == 'bulk':
            # Adding the newly calculated primitive and conventional cells to the ModelSystem
            (
                primitive_cell,
                conventional_cell,
            ) = self.resolve_bulk_symmetry(model_system=model_system, logger=logger)
            if primitive_cell:
                model_system.representations.append(primitive_cell)
            if conventional_cell:
                model_system.representations.append(conventional_cell)


# Backward compatibility alias
Symmetry = GlobalCrystalSymmetry


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


# Add backward compatibility property for surface_area -> boundary_area using lambdas
setattr(
    Representation,
    'surface_area',
    property(
        lambda self: self.boundary_area,
        lambda self, value: setattr(self, 'boundary_area', value),
    ),
)


class ModelSystem(System, Representation):
    """
    Model system used as an input for simulating the material.

    Particle positions are held at the top level in the quantity "positions"
    and more detailed per‐particle information, e.g., electronic state information,
    are stored in the subsection "particle_states". The particle state can be of type
    AtomState or CGBeadState, but the list of particle states must be homogeneous in type.
    Mixed systems should be treated with multiple ModelSystem sections.

    Downstream subsystems refer to atoms via particle_indices.

    Definitions:
        - `name` refers to all the verbose and user-dependent naming in ModelSystem,
        - `type` refers to the type of the ModelSystem (atom, bulk, surface, etc.),
        - `dimensionality` refers to the dimensionality of the ModelSystem (0, 1, 2, 3),

    If the ModelSystem `is_representative`, proceeds with normalization. The time evolution of the
    ModelSystem is stored in a `list` format under `Simulation`, and for each element of that list,
    `time_step` can be defined.

    It is composed of the sub-sections:
        - `Representation` containing alternative representations of the system
        - `GlobalSymmetry` containing the global symmetry information for bulk ModelSystem,
        - `ChemicalFormula` containing the information of the chemical formulas in different
        formats.

    This class nests over itself (with the section proxy in `sub_systems`) to define different
    parent-child system trees. The quantities `branch_label`, `branch_depth`, `particle_indices`,
    and `bond_list` are used to define the parent-child tree.

    See the [ModelSystem documentation](https://nomad-lab.eu/prod/v1/staging/docs/howto/customization/plugins_dev.html)
    for comprehensive usage examples, design philosophy, and integration patterns.

    The normalization within ModelSystem.normalize() proceeds in the following order:
        1. Parent System normalization
        2. Particle state reassignment and validation
        3. System type and dimensionality resolution (if representative and atomic)
        4. Symmetry section creation and normalization (for bulk systems)
        5. ChemicalFormula section creation and normalization

    Note: Other normalizations (ParticleState, ElectronicState, etc.) are handled automatically
    by NOMAD's normalization system when their respective sections are processed.

    Examples for the parent-child hierarchical trees:

        - Example 1, a crystal Si has: 2 alternative Representation sections (named 'primitive'
        and 'conventional'), 1 Symmetry section, and 0 nested ModelSystem trees. The original
        representation data is stored directly on the ModelSystem instance itself.

        - Example 2, an heterostructure Si/GaAs has: 1 parent ModelSystem section (for
        Si/GaAs together) and 2 nested child ModelSystem sections (for Si and GaAs); each
        child has 2 alternative Representation sections and 1 Symmetry section. The parent
        ModelSystem section could also have 2 alternative Representation sections and 1
        Symmetry section (if it is possible to extract them).

        - Example 3, a solution of C800H3200Cu has: 1 parent ModelSystem section (for
        800*(CH4)+Cu) and 2 nested child ModelSystem sections (for CH4 and Cu). Each system
        stores its cell data directly via Representation inheritance.

        - Example 4, a passivated surface GaAs-CO2 has --> similar to the example 2.

        - Example 5, a passivated heterostructure Si/(GaAs-CO2) has: 1 parent ModelSystem
        section (for Si/(GaAs-CO2)), 2 child ModelSystem sections (for Si and GaAs-CO2),
        and 2 additional children sections in one of the children (for GaAs and CO2). The number
        of Cell and Symmetry sections can be inferred using a combination of example
        2 and 3.
    """

    normalizer_level = 0

    name = Quantity(
        type=str,
        description="""
        Any verbose naming refering to the ModelSystem. Can be left empty if it is a simple
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
    )  # TODO: remove, as main ModelSystem is now representative by default

    # ? Check later when implementing `Outputs` if this quantity needs to be extended
    time_step = Quantity(
        type=np.int32,
        description="""
        Specific time snapshot of the ModelSystem. The time evolution is then encoded
        in a list of ModelSystems under Computation where for each element this quantity defines
        the time step.
        """,
    )

    symmetry = SubSection(sub_section=GlobalSymmetry.m_def)

    chemical_formula = SubSection(sub_section=ChemicalFormula.m_def)

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

    # positions is defined in ModelSystem (not Representation) because it represents the fixed
    # Cartesian positions of atoms in the top-level system. Alternative representations can have
    # different lattice_vectors and fractional_coordinates, but they all describe the same atoms
    # at the same Cartesian positions. Subsystems reference these positions via particle_indices.
    positions = Quantity(
        type=np.float64,
        shape=['*', 3],
        unit='meter',
        description="""
        Cartesian coordinates of all atoms in the system. Values are expressed in an implicit
        Cartesian coordinate system with axes ordered as (x, y, z). The orientation of this
        frame is determined by the simulation code or parser that generates the data.
        All subsystems reference these positions via particle_indices.
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

    electronic_state = SubSection(
        section_def=ElectronicState.m_def,
        description="""
        Electronic state of the system, e.g., the electronic structure information.
        This is an starting point for navigating the electronic hierarchy.
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

    representations = SubSection(
        sub_section=AlternativeRepresentation.m_def,
        repeats=True,
        description="""
        Alternative representations of the original model system, e.g., in a different simulation box or crystal cell.
        """,
    )

    sub_systems = SubSection(sub_section=SectionProxy('ModelSystem'), repeats=True)

    def __init__(self, m_def: 'Section' = None, m_context: 'Context' = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        self._cache: dict[str, Any] = {}

    @log(exc_msg='Failed to extract geometric-space data from ASE cell')
    def get_geometric_space_for_cell(self) -> None:
        """
        Get the real space parameters for the cell using ASE.
        """
        logger = self.get_geometric_space_for_cell.__annotations__['logger']

        atoms = self.to_ase_atoms(
            representation_index=0 if self.representations else None, logger=logger
        )
        if atoms is None:
            return  # parent already logged the problem

        cell = atoms.get_cell()
        if self.representations and len(self.representations) > 0:
            cell_section = self.representations[0]
            cell_section.volume = cell.volume * ureg.angstrom**3

    def compute_fractional_coordinates(
        self,
        positions: np.ndarray | None = None,
        lattice_vectors: np.ndarray | None = None,
    ) -> np.ndarray | None:
        """
        Compute fractional coordinates from Cartesian positions and lattice vectors
        by solving: fractional = positions @ inv(lattice_vectors.T)

        Args:
            `positions`: Cartesian positions in the implicit frame (N x 3 array). If `None`, uses self.positions.
            `lattice_vectors`: Lattice vectors as 3x3 matrix (rows are vectors a,b,c). If `None`, uses self.lattice_vectors.

        Returns:
            Fractional coordinates (N x 3 array) or `None` if computation fails.
        """
        # TODO: Extend support to 2D and 1D systems by handling reduced-dimension lattice vectors appropriately.
        # Use instance attributes if not provided
        if positions is None:
            if self.positions is None:
                return None
            positions = (
                self.positions.magnitude
                if hasattr(self.positions, 'magnitude')
                else self.positions
            )

        if lattice_vectors is None:
            if self.lattice_vectors is None:
                return None
            lattice_vectors = (
                self.lattice_vectors.magnitude
                if hasattr(self.lattice_vectors, 'magnitude')
                else self.lattice_vectors
            )

        # Check for degenerate cell  #? move to a separate utility function
        try:
            cell_volume = np.linalg.det(lattice_vectors)
            # Use a relative threshold instead of absolute since values can be in different units
            if abs(cell_volume) < 1e-50:
                return None

            # Compute fractional coordinates: fractional = positions @ inv(lattice_vectors)
            # This solves: positions = fractional @ lattice_vectors
            # (lattice_vectors rows are the basis vectors a, b, c)
            inv_lattice = np.linalg.inv(lattice_vectors)
            fractional = positions @ inv_lattice

            return fractional
        except (np.linalg.LinAlgError, ValueError):
            return None

    # TODO this could be wrong if executed before normalization
    def is_atomic(self) -> bool:
        """
        Determine if the system can be classified as "atomic".

        Criterion:
          - ASE must be able to map all labels/symbols in the particle_states subsection
        to atomic numbers.
          - The particle_states cannot contain only CGBeadState objects.

        Example Usages:
          - Decide whether to use AtomState. `is_atomic` must return True for all downstream functionalities to work properly.

        Args:
            logger (BoundLogger): The logger to log messages.
        Returns:
            bool: True if all chemical symbols are valid, False otherwise.
        """

        if self._cache.get('is_atomic') is not None:
            return self._cache['is_atomic']

        symbols = self.get_symbols()
        is_atomic = self._all_labels_are_elements(symbols)

        is_atomic = (
            not all(isinstance(p, CGBeadState) for p in self.particle_states)
            if is_atomic
            else False
        )

        self._cache['is_atomic'] = is_atomic
        return is_atomic

    def get_symbols(self) -> list[str]:
        """
        Access to particle labels, irrespective of specific child class.

        Returns [] if any particle lacks a usable label/symbol.
        """
        if self._cache.get('symbols') is not None:
            return self._cache['symbols']

        # root
        symbols: list[str] = []
        if self.is_root_system():
            symbols = [ps.get_label() for ps in self.particle_states]
            if not self.particle_states or None in symbols:
                symbols = []
            self._cache['symbols'] = symbols

            return symbols

        # child: slice the labels from root with particle_indices
        root = self.get_root_system()
        root_syms = root.get_symbols()
        if not root_syms or self.particle_indices is None:
            symbols = []
        # Validate indices: must be ints and 0 <= i < len(root_syms)
        elif any(i < 0 or i >= len(root_syms) for i in self.particle_indices):
            symbols = []
        else:
            try:
                symbols = [root_syms[i] for i in self.particle_indices]
            except Exception:
                symbols = []

        self._cache['symbols'] = symbols
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
    def to_ase_atoms(
        self, representation_index: int | None = None
    ) -> 'ase.Atoms | None':
        """
        Generates an ASE Atoms object from ModelSystem data.

        Args:
            representation_index: Index of the alternative representation to use for cell geometry.
                                 - None (default): Uses the original cell data directly from ModelSystem
                                   (lattice_vectors, periodic_boundary_conditions)
                                 - int: Uses the alternative representation at ModelSystem.representations[index]
                                   This allows conversion of primitive cells, conventional cells, or other
                                   geometric views to ASE format while keeping the same atomic positions.

        Uses:
          - atom_states to obtain chemical symbols
          - positions from the top-level positions quantity (always from ModelSystem, not from representations)
          - periodic boundary conditions and lattice vectors from either ModelSystem directly (if representation_index=None)
            or from the specified alternative representation (if representation_index is an integer)
        """
        logger = self.to_ase_atoms.__annotations__['logger']
        symbols = self.get_symbols()
        if not symbols:
            logger.error('Cannot generate ASE Atoms without chemical symbols.')
            return None
        if not self._all_labels_are_elements(symbols):
            logger.error(
                'Cannot generate ASE Atoms: symbols are not all element symbols.'
            )
            return None

        ase_atoms = ase.Atoms(symbols=symbols)

        # Determine cell information source based on representation_index
        if representation_index is None:
            logger.info(
                'Using original ModelSystem data (no representation specified).'
            )
            # Use original ModelSystem's lattice vectors and PBC
            if self.periodic_boundary_conditions is not None:
                ase_atoms.set_pbc(self.periodic_boundary_conditions)
            else:
                ase_atoms.set_pbc([False, False, False])

            if self.lattice_vectors is not None:
                ase_atoms.set_cell(self.lattice_vectors.to('angstrom').magnitude)
            else:
                logger.info('No lattice_vectors found in original ModelSystem data.')
        else:
            # Use specified representation
            if not self.representations:
                logger.info('No representations available in ModelSystem.')
            if representation_index >= len(self.representations):
                logger.debug(
                    'Representation index out of range.',
                    representation_index=representation_index,
                    available_range=range(len(self.representations)),
                )

            cell_section = self.representations[representation_index]

            if cell_section.periodic_boundary_conditions is None:
                logger.info(
                    f'Representation[{representation_index}] periodic_boundary_conditions not found; using default [False, False, False].'
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
                logger.info(
                    'No lattice_vectors found in representations.',
                    representation_index=representation_index,
                )

        # Check that positions have been set on the ModelSystem
        if self.positions is None:
            logger.error('ModelSystem.positions is not defined.')
            return None
        else:
            ase_atoms.set_positions(self.positions.to('angstrom').magnitude)
        return ase_atoms

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
            elif isinstance(classification, Class2D | Material2D):
                system_type = '2D'
                dimensionality = 2
        else:
            logger.info(
                'ModelSystem.type and dimensionality analysis not run due to large system size.'
            )

        return system_type, dimensionality

    # TODO thorough check
    def _copy_common_quantities(
        self, src, dst, *, exclude: set[str] | None = None
    ) -> None:
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
        Cases for particle state reassignment:
          1. The parser populated any generic ParticleState entries
          2. The parser populated mixed AtomState/CGBeadState particle state lists
          3. The parser incorrected populated AtomState instances when *any* of the
          particle labels are not valid element symbols.

        The reassignment will convert *all* particle states to either:
          - AtomsState if all labels are valid element symbols, else
          - CGBeadState.

        Notes:
          - Mixed systems are not allowed.
          - If the parser populates all CGBeadState instances, no reassignment is done regardless of the particle labels.
        """
        if not self.particle_states:
            return

        ps_list = list(self.particle_states)

        labels = self.get_symbols()
        is_atomic = self._all_labels_are_elements(labels)
        is_cg = all(isinstance(p, CGBeadState) for p in ps_list)
        if is_cg:
            return

        if is_atomic and not all(
            isinstance(p, AtomsState | CGBeadState) for p in ps_list
        ):
            # Map one-to-one using validated element labels
            self._clear_particle_states_inplace()
            for old, lab in zip(ps_list, labels):
                new = AtomsState()
                new.chemical_symbol = lab  # validated by symbols2numbers + MEnum on set
                # Copy all overlapping fields EXCEPT chemical_symbol (we just set it)
                self._copy_common_quantities(old, new, exclude={'chemical_symbol'})
                new.normalize(archive, logger)
                self.particle_states.append(new)
        elif not is_atomic and not is_cg:
            # Fall back to CG; use each original ParticleState.label (may be None)
            self._clear_particle_states_inplace()
            for old in ps_list:
                lab = old.label
                new = CGBeadState()
                if lab:
                    new.bead_symbol = lab
                # Copy all overlapping fields EXCEPT bead_symbol (we just set it)
                self._copy_common_quantities(old, new, exclude={'bead_symbol'})
                new.normalize(archive, logger)
                self.particle_states.append(new)

    def _validate_subsystem(self, logger: 'BoundLogger') -> None:
        """ """

        if self.is_root_system():
            return

        if self.particle_indices is None:
            logger.warning(
                'Cannot validate ModelSystem subsystem without particle_indices.'
            )
            return

        parent = self.m_parent
        if parent.is_root_system():
            n_particles = (
                len(parent.positions) if parent.positions is not None else None
            )
            if not n_particles:
                logger.error(
                    'Cannot validate ModelSystem subsystem without root particle positions.'
                )
                return

            assert all(0 <= i < n_particles for i in self.particle_indices), (
                'Invalid particle_indices in ModelSystem subsystem.'
            )
            return

        if parent.particle_indices is None:
            logger.error(
                'Cannot validate ModelSystem subsystem without parent particle_indices.'
            )
            return

        assert all(pi in parent.particle_indices for pi in self.particle_indices), (
            'Invalid particle_indices in ModelSystem subsystem.'
        )

        # TODO logger.warning or logger.error in each case?

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Tasks executed:

        - Generate primitive and conventional representations for bulk systems
        - Populate symmetry information
        - Create chemical formulas
        - Perform structural analysis and classification
        """

        super().normalize(archive, logger)

        # Check and normalize periodic boundary conditions based on lattice vectors
        is_lattice_vectors_empty: bool = (
            self.lattice_vectors is None
            or (
                hasattr(self.lattice_vectors, 'size') and self.lattice_vectors.size == 0
            )
            or (
                hasattr(self.lattice_vectors, '__len__')
                and len(self.lattice_vectors) == 0
            )
        )
        if is_lattice_vectors_empty and self.periodic_boundary_conditions:
            logger.warning(
                'Lattice vectors are not defined but periodic boundary conditions are set. Unsetting PBC.'
            )
            self.periodic_boundary_conditions = []

        # reassign particle states according to label validity
        self._reassign_generic_particle_states(archive, logger)
        # Validate the ModelSystem subsystem
        self._validate_subsystem(logger)

        # Prevent representative subsystems
        if self.is_representative and not self.is_root_system():
            logger.warning(
                'ModelSystem.is_representative is set to True for a subsystem. '
                'Setting to False'
            )
            self.is_representative = False
        # Skip the following normalization if system is not representative
        if not self.is_representative:
            return

        ## ATOMIC NORMALIZATION
        if not self.is_atomic():
            return
        # Generate ASE Atoms object from top-level ModelSystem data
        ase_atoms = self.to_ase_atoms(
            representation_index=0 if self.representations else None, logger=logger
        )
        if ase_atoms is None:
            logger.error('Could not generate ASE Atoms from ModelSystem.')
            return

        # Resolve system type and dimensionality using ASE atoms
        self.type, self.dimensionality = self.resolve_system_type_and_dimensionality(
            ase_atoms, logger
        )

        # Extract geometric space quantities for the cell
        self.get_geometric_space_for_cell(logger=logger)

        # TODO: Optionally populate fractional_coordinates from positions and lattice_vectors
        # This could be controlled via an environment variable (e.g., NOMAD_POPULATE_FRACTIONAL_COORDS)
        # if os.getenv('NOMAD_POPULATE_FRACTIONAL_COORDS', 'false').lower() == 'true':
        #     if self.positions is not None and self.lattice_vectors is not None:
        #         self.fractional_coordinates = self.compute_fractional_coordinates()

        # Create and normalize Symmetry section if applicable
        if self.type == 'bulk' and self.symmetry is None:
            self.symmetry = GlobalCrystalSymmetry()
            self.symmetry.normalize(archive, logger)

        # Create and normalize ChemicalFormula section
        if atom_labels := self.get_symbols():
            sec_chemical_formula = self.m_create(ChemicalFormula)
            sec_chemical_formula.resolve_chemical_formulas(
                Formula(formula=''.join(atom_labels))
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

    def is_root_system(self) -> bool:
        """
        True if this node has no parent or its parent is not a ModelSystem.
        Prefer an ``isinstance`` check; fall back to comparing ``m_def`` to handle
        proxy/wrapper parents that still expose a ModelSystem definition.
        """

        parent = self.m_parent
        return (parent is None) or not (
            isinstance(parent, ModelSystem) or parent.m_def is ModelSystem.m_def
        )

    def get_root_system(self) -> 'ModelSystem':
        """
        Walk up through parents until reaching the root. Detect and fail on cycles.

        Returns
        -------
        ModelSystem
            The root system.

        Raises
        ------
        RuntimeError
            If a cycle is detected in the parent chain.
        """
        node = self
        seen = {id(node)}

        while not node.is_root_system():
            parent = node.m_parent
            if parent is None:
                break
            if id(parent) in seen:
                raise RuntimeError('Cycle detected in ModelSystem parent chain.')
            seen.add(id(parent))
            node = parent

        return node

    # functions for working with molecules
    def get_bond_list(self) -> np.ndarray:
        """
        Retrieves the bond list for this subsystem by filtering the root bond_list
        using the subsystem's `particle_indices`. The bond indices remain in root-level
        coordinates (no reindexing).

        Args:
            set_local (bool): If True, sets `self.bond_list` to the filtered bonds.

        Returns:
            np.ndarray: Filtered bond list for this subsystem (root-level indices).
        """
        if self._cache.get('bond_list') is not None:
            return self._cache['bond_list']

        bond_list: np.ndarray = np.empty((0, 2), dtype=np.int32)
        # root
        if self.is_root_system():
            bond_list = self.bond_list if self.bond_list is not None else bond_list
            self._cache['bond_list'] = bond_list

            return bond_list

        # child
        root = self.get_root_system()
        if self.particle_indices is None or root.bond_list is None:
            return bond_list

        idx: np.ndarray = (
            np.asarray(self.particle_indices, dtype=np.int32).ravel()
            if self.particle_indices is not None
            else np.empty(0, dtype=np.int32)
        )

        mask = np.isin(root.bond_list, idx).all(axis=1)
        root_bonds_temp = np.asarray(root.bond_list, dtype=np.int32).reshape(-1, 2)
        root_bonds: np.ndarray = root_bonds_temp.astype(np.int32)
        filtered_bonds: np.ndarray = root_bonds[mask].astype(np.int32)
        bond_list = np.unique(filtered_bonds, axis=0).astype(np.int32)
        self._cache['bond_list'] = bond_list

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
        bonds = self.get_bond_list()

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
        graph: nx.Graph = nx.Graph()
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

    @log
    @staticmethod
    def from_ase_atoms(ase_atoms: ase.Atoms) -> 'ModelSystem':
        """
        Creates a clean ModelSystem and populate it with data from an ASE Atoms object.
        It does NOT modify the existing ModelSystem instance. Can be called from the class, without instantiating first.

        The function maps the following ASE properties to ModelSystem:
        - Particle states: chemical symbols, atomic numbers, initial charges, tags as labels
        - Positions: Cartesian and fractional coordinates
        - Cell data: lattice vectors, periodic boundary conditions
        - Geometric extents: volume (3D), area (2D), or length (1D) based on dimensionality
        - Dynamics: velocities (if available)

        The returned ModelSystem is NOT normalized and contains no derived data.
        To get primitive/conventional representations and other derived properties, call
        ModelSystem.normalize() afterwards.

        Args:
            ase_atoms: The ASE Atoms object to convert

        Returns:
            ModelSystem: A clean ModelSystem with basic particle and cell data (not normalized)
        """

        logger = ModelSystem.from_ase_atoms.__annotations__['logger']
        model_system = ModelSystem()

        # Get ASE arrays for additional properties
        has_initial_charges = ase_atoms.has('initial_charges')
        has_tags = ase_atoms.has('tags')
        has_velocities = ase_atoms.has('momenta') or hasattr(ase_atoms, '_velocities')

        # Add particle states from ASE atoms with additional properties
        for i, (symbol, atomic_number) in enumerate(
            zip(ase_atoms.get_chemical_symbols(), ase_atoms.get_atomic_numbers())
        ):
            state = AtomsState(chemical_symbol=symbol, atomic_number=atomic_number)

            # Map initial charges if available
            if has_initial_charges:
                try:
                    initial_charges = ase_atoms.get_initial_charges()
                    if len(initial_charges) > i:
                        # Convert to integer charge (round to nearest integer)
                        charge = int(round(initial_charges[i]))
                        if charge != 0:  # Only set non-zero charges
                            state.charge = charge
                except Exception as e:
                    logger.debug('Could not map initial charges', error=str(e))

            # Map tags as labels if available
            if has_tags:
                try:
                    tags = ase_atoms.get_tags()
                    if len(tags) > i and tags[i] != 0:  # Only set non-zero tags
                        state.label = f'{symbol}_{tags[i]}'
                except Exception as e:
                    logger.debug('Could not map tags', error=str(e))

            model_system.particle_states.append(state)

        # Set positions
        positions = ase_atoms.get_positions()
        if not positions.tolist():
            logger.debug('ASE Atoms has no positions.')

        model_system.positions = positions * ureg('angstrom')
        model_system.n_particles = len(model_system.positions)

        # Set cell information at ModelSystem level (original data)
        cell = ase_atoms.get_cell()
        pbc = ase_atoms.get_pbc()
        model_system.lattice_vectors = ase.geometry.complete_cell(cell) * ureg(
            'angstrom'
        )
        model_system.periodic_boundary_conditions = pbc

        # Set fractional coordinates if we have a proper cell
        try:
            if cell.volume > 1e-10:  # Check for non-degenerate cell
                scaled_positions = ase_atoms.get_scaled_positions()
                model_system.fractional_coordinates = scaled_positions
        except Exception as e:
            logger.debug('Could not compute fractional coordinates', error=str(e))

        # Set volume/area/length based on dimensionality and cell structure
        try:
            cell = ase_atoms.get_cell()
            pbc = ase_atoms.get_pbc()

            # Count non-degenerate lattice vectors
            lattice_vectors = [v for v in cell if np.linalg.norm(v) > 1e-10]
            n_lattice_vectors = len(lattice_vectors)
            n_periodic_dims = sum(pbc)

            if n_lattice_vectors >= 3 and n_periodic_dims >= 3:
                # True 3D system - use volume
                volume = ase_atoms.get_volume()
                if volume > 1e-10:  # Check for reasonable volume
                    model_system.volume = volume * ureg('angstrom**3')
            elif n_lattice_vectors >= 3 and n_periodic_dims == 2:
                # 2D system with vacuum - still use volume (includes vacuum)
                volume = ase_atoms.get_volume()
                if volume > 1e-10:
                    model_system.volume = volume * ureg('angstrom**3')
            elif n_lattice_vectors >= 3 and n_periodic_dims == 1:
                # 1D system with vacuum - still use volume (includes vacuum)
                volume = ase_atoms.get_volume()
                if volume > 1e-10:
                    model_system.volume = volume * ureg('angstrom**3')
            elif n_lattice_vectors == 2 and n_periodic_dims <= 2:
                # True 2D system - compute area from cross product
                area = np.linalg.norm(np.cross(lattice_vectors[0], lattice_vectors[1]))
                if area > 1e-10:
                    model_system.area = area * ureg('angstrom**2')
            elif n_lattice_vectors == 1 and n_periodic_dims <= 1:
                # True 1D system - use length of single lattice vector
                length = np.linalg.norm(lattice_vectors[0])
                if length > 1e-10:
                    model_system.length = length * ureg('angstrom')
        except Exception as e:
            logger.debug(f'Could not compute geometric extents: {e}')

        # Set velocities if available
        if has_velocities:
            try:
                velocities = ase_atoms.get_velocities()
                if velocities is not None and len(velocities) == len(positions):
                    model_system.velocities = velocities * ureg('angstrom/second')
            except Exception as e:
                logger.debug(f'Could not map velocities: {e}')

        return model_system
