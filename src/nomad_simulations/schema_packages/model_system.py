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

from nomad_simulations.schema_packages.utils import log

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from typing import Any, Optional

    import pint
    from nomad.datamodel.datamodel import EntryArchive
    from nomad.metainfo import Context, Section
    from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.atoms_state import (
    AtomsState,
    CGBeadState,
    ParticleState,
)
from nomad_simulations.schema_packages.utils import get_sibling_section

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
        | cartesian  | coordinate system with fixed angles between the axes (not necessarily 90°) | 1, 2, 3 | x, y, z |
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
    )

    transformation_matrix = Quantity(
        type=np.float64,
        shape=[3, 3],
        description="""
        Matrix `P` used to transform the custom coordinates system to the global coordinates system.
        Together with the vector `p` (stored in origin_shift), the transformation between
        the custom coordinates `x` and global coordinates `X` is then given by:
            `x` = `P` `X` + `p`.
        """,
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
    def get_geometric_space_for_atomic_cell(self) -> None:
        """
        Get the real space parameters for the atomic cell using ASE.
        to_ase_atoms live under the parent ModelSystem.

        Args:
            logger (BoundLogger): The logger to log messages.
        """
        logger = self.get_geometric_space_for_atomic_cell.__annotations__['logger']
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
        self.get_geometric_space_for_atomic_cell(logger=logger)


class Symmetry(ArchiveSection):
    """
    A base section used to specify the symmetry of the `AtomicCell`.

    Note: this information can be extracted via normalization using the MatID package, if `AtomicCell`
    is specified.
    """

    bravais_lattice = Quantity(
        type=str,
        description="""
        Bravais lattice in Pearson notation.

        The first lowercase letter identifies the
        crystal family: a (triclinic), b (monoclinic), o (orthorhombic), t (tetragonal),
        h (hexagonal), c (cubic).

        The second uppercase letter identifies the centring: P (primitive), S (face centered),
        I (body centred), R (rhombohedral centring), F (all faces centred).
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

    atomic_cell_ref = Quantity(
        type=Cell,
        description="""
        Reference to the AtomicCell section that the symmetry refers to.
        """,
    )

    def resolve_analyzed_atomic_cell(
        self,
        symmetry_analyzer: 'SymmetryAnalyzer',
        cell_type: str,
        logger: 'BoundLogger',
    ) -> 'Cell | None':
        """
        Resolves the `AtomicCell` section from the `SymmetryAnalyzer` object and the cell_type
        (primitive or conventional).

        Args:
            symmetry_analyzer (SymmetryAnalyzer): The `SymmetryAnalyzer` object used to resolve.
            cell_type (str): The type of cell to resolve, either 'primitive' or 'conventional'.
            logger (BoundLogger): The logger to log messages.

        Returns:
            (Optional[AtomicCell]): The resolved `AtomicCell` section or None if the cell_type
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
            logger.error(f'Cell type {cell_type} is not supported.')
            return None

        try:
            wyckoff = mapping['wyckoff']()
            equivalent_atoms = mapping['equivalent']()
            system = mapping['system']()
        except Exception as e:
            logger.error('Error extracting symmetry data', exc_info=e)
            return None

        cell = system.get_cell()

        # Create the cell (or atomic cell) for geometry only
        atomic_cell = AtomicCell(type=cell_type)
        atomic_cell.lattice_vectors = cell * ureg.angstrom
        # ! Positions are stored directly under model_system in nomad-simulations>=0.4.
        atomic_cell.wyckoff_letters = wyckoff
        atomic_cell.equivalent_atoms = equivalent_atoms
        atomic_cell.get_geometric_space_for_atomic_cell(logger=logger)
        return atomic_cell

    def resolve_bulk_symmetry(
        self, original_atomic_cell: 'AtomicCell', logger: 'BoundLogger'
    ) -> 'tuple[AtomicCell | None, AtomicCell | None]':
        """
        Resolves the symmetry of the material being simulated using MatID and the
        originally parsed data under original_atomic_cell. It generates two other
        `AtomicCell` sections (the primitive and standarized cells), as well as populating
        the `Symmetry` section.

        Args:
            original_atomic_cell (AtomicCell): The `AtomicCell` section that the symmetry
            uses to in MatID.SymmetryAnalyzer().
            logger (BoundLogger): The logger to log messages.
        Returns:
            primitive_atomic_cell, conventional_atomic_cell (tuple[Optional[AtomicCell], Optional[AtomicCell]]): The primitive and standardized `AtomicCell` sections.
        """
        symmetry = {}
        try:
            ase_atoms = self.m_parent.to_ase_atoms(logger=logger)
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
        symmetry['bravais_lattice'] = symmetry_analyzer.get_bravais_lattice()
        symmetry['hall_symbol'] = symmetry_analyzer.get_hall_symbol()
        symmetry['point_group_symbol'] = symmetry_analyzer.get_point_group()
        symmetry['space_group_number'] = symmetry_analyzer.get_space_group_number()
        symmetry['space_group_symbol'] = (
            symmetry_analyzer.get_space_group_international_short()
        )
        symmetry['origin_shift'] = symmetry_analyzer._get_spglib_origin_shift()
        symmetry['transformation_matrix'] = (
            symmetry_analyzer._get_spglib_transformation_matrix()
        )

        # Populating the originally parsed AtomicCell wyckoff_letters and equivalent_atoms information
        original_wyckoff = symmetry_analyzer.get_wyckoff_letters_original()
        original_equivalent_atoms = symmetry_analyzer.get_equivalent_atoms_original()
        original_atomic_cell.wyckoff_letters = original_wyckoff
        original_atomic_cell.equivalent_atoms = original_equivalent_atoms

        # Populating the primitive AtomState information
        primitive_atomic_cell = self.resolve_analyzed_atomic_cell(
            symmetry_analyzer=symmetry_analyzer, cell_type='primitive', logger=logger
        )

        # Populating the conventional AtomState information
        conventional_atomic_cell = self.resolve_analyzed_atomic_cell(
            symmetry_analyzer=symmetry_analyzer, cell_type='conventional', logger=logger
        )

        # Getting prototype_formula, prototype_aflow_id, and strukturbericht designation from
        # standarized Wyckoff numbers and the space group number
        if symmetry.get('space_group_number'):
            # Retrieve the expanded conventional system (an ASE.Atoms object) from the analyzer.
            conventional_system = symmetry_analyzer.get_conventional_system()
            # Use the conventional system to get the expanded atomic numbers.
            conventional_num = conventional_system.get_atomic_numbers()
            conventional_wyckoff = conventional_atomic_cell.wyckoff_letters
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

        return primitive_atomic_cell, conventional_atomic_cell

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        atomic_cell = get_sibling_section(
            section=self, sibling_section_name='cell', logger=logger
        )
        # TODO : the following is a temporary fix, and it might break again
        # when there are systems with deeper hierarchies.
        if self.m_parent.m_parent is not None and self.m_parent.type == 'bulk':
            # Adding the newly calculated primitive and conventional cells to the ModelSystem
            (
                primitive_atomic_cell,
                conventional_atomic_cell,
            ) = self.resolve_bulk_symmetry(
                original_atomic_cell=atomic_cell, logger=logger
            )
            self.m_parent.m_add_sub_section(ModelSystem.cell, primitive_atomic_cell)
            self.m_parent.m_add_sub_section(ModelSystem.cell, conventional_atomic_cell)
            # Reference to the standarized cell, and if not, fallback to the originally parsed one
            self.atomic_cell_ref = self.m_parent.cell[-1]


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

    Particle positions are held at the top level in the quantity “positions”
    and more detailed per‐particle information, e.g., electronic state information,
    are stored in the subsection “particle_states”. The particle state can be of type
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
        - `Symmetry` containing the information of the (conventional) atomic cell symmetry
        in bulk ModelSystem,
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

    Examples for the parent-child hierarchical trees:

        - Example 1, a crystal Si has: 3 AtomicCell sections (named 'original', 'primitive',
        and 'conventional'), 1 Symmetry section, and 0 nested ModelSystem trees.

        - Example 2, an heterostructure Si/GaAs has: 1 parent ModelSystem section (for
        Si/GaAs together) and 2 nested child ModelSystem sections (for Si and GaAs); each
        child has 3 AtomicCell sections and 1 Symmetry section. The parent ModelSystem section
        could also have 3 AtomicCell and 1 Symmetry section (if it is possible to extract them).

        - Example 3, a solution of C800H3200Cu has: 1 parent ModelSystem section (for
        800*(CH4)+Cu) and 2 nested child ModelSystem sections (for CH4 and Cu); each child
        has 1 AtomicCell section.

        - Example 4, a passivated surface GaAs-CO2 has --> similar to the example 2.

        - Example 5, a passivated heterostructure Si/(GaAs-CO2) has: 1 parent ModelSystem
        section (for Si/(GaAs-CO2)), 2 child ModelSystem sections (for Si and GaAs-CO2),
        and 2 additional children sections in one of the children (for GaAs and CO2). The number
        of AtomicCell and Symmetry sections can be inferred using a combination of example
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

    cell = SubSection(sub_section=Cell.m_def, repeats=True)

    symmetry = SubSection(sub_section=Symmetry.m_def, repeats=True)

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
        self._cache: dict[str, Any] = {}

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

    @log
    def get_symbols(self) -> list[str]:
        """
        Access to particle labels, irrespective of specific child class.

        Returns [] if any particle lacks a usable label/symbol.
        """
        # TODO Should we log something here?
        # logger = self.get_symbols.__annotations__['logger']
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
    def to_ase_atoms(self) -> 'ase.Atoms | None':
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
        if not self._all_labels_are_elements(symbols):
            logger.error(
                'Cannot generate ASE Atoms: symbols are not all element symbols.'
            )
            return None

        ase_atoms = ase.Atoms(symbols=symbols)

        # Use cell data (from the first cell) for periodic boundary conditions and lattice
        if self.cell and len(self.cell) > 0:
            cell_section = self.cell[0]
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
                logger.info('No lattice_vectors found in cell[0].')
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
        if self.cell and len(self.cell) > 0:
            cell = ase_atoms.get_cell()
            self.cell[0].lattice_vectors = ase.geometry.complete_cell(cell) * ureg(
                'angstrom'
            )
            self.cell[0].periodic_boundary_conditions = ase_atoms.get_pbc()

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

        labels = self.get_symbols(logger=logger)
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
        super().normalize(archive, logger)

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
        ase_atoms = self.to_ase_atoms(logger=logger)
        if ase_atoms is None:
            logger.error('Could not generate ASE Atoms from ModelSystem.')
            return

        # Resolve system type and dimensionality using ASE atoms
        self.type, self.dimensionality = self.resolve_system_type_and_dimensionality(
            ase_atoms, logger
        )

        # Create and normalize Symmetry section if applicable
        if self.type == 'bulk' and self.symmetry is not None:
            sec_symmetry = self.m_create(Symmetry)
            sec_symmetry.normalize(archive, logger)

        # Create and normalize ChemicalFormula section
        sec_chemical_formula = self.m_create(ChemicalFormula)
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

        bond_list = np.empty((0, 2), dtype=np.int32)
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
        root_bonds = np.asarray(root.bond_list, dtype=np.int32).reshape(-1, 2)
        bond_list = root_bonds[mask]
        bond_list = np.unique(bond_list, axis=0)
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
