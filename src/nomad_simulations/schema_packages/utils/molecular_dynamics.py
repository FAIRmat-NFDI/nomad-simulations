from __future__ import annotations

from array import array
from collections import namedtuple
from collections.abc import Callable
from itertools import chain
from typing import TYPE_CHECKING, Any, TypedDict

import ase
import numpy as np
from scipy import sparse
from scipy.stats import linregress
from structlog.stdlib import BoundLogger

from nomad_simulations.schema_packages.force_field import (
    ForceField,
    ParticleParametersContainer,
)

try:
    import MDAnalysis
    import MDAnalysis.analysis.rdf as MDA_RDF
    from MDAnalysis.core._get_readers import get_reader_for
    from MDAnalysis.core.topology import Topology
    from MDAnalysis.core.universe import Universe

    _HAS_MDA = True
except ImportError:
    _HAS_MDA = False
    MDAnalysis = None  # type: ignore

try:
    import networkx

    _HAS_NETWORKX = True
except ImportError:
    _HAS_NETWORKX = False
    networkx = None  # type: ignore

# Import types for type checking only (not at runtime)
if TYPE_CHECKING:
    from MDAnalysis import Universe as MDAUniverse
    from MDAnalysis.core.groups import AtomGroup

from nomad import atomutils
from nomad.metainfo import MEnum, MSection, Quantity, Reference, Section, SubSection
from nomad.units import ureg
from nomad.utils import get_logger

from nomad_simulations.schema_packages.model_system import ModelSystem

LOGGER = get_logger(__name__)


class MolecularRDFResults(TypedDict):
    """Type definition for molecular radial distribution function results."""

    n_smooth: int
    n_prune: int
    type: str
    types: list[str]
    variables_name: list[list[str]]
    bins: list[Any]  # list of pint Quantity arrays
    value: list[np.ndarray]
    frame_start: list[int]
    frame_end: list[int]


class MolecularMSDResults(TypedDict):
    """Type definition for molecular mean squared displacement results."""

    type: str
    direction: str
    types: list[str]
    times: np.ndarray  # pint Quantity array
    value: np.ndarray  # pint Quantity array
    diffusion_constant: np.ndarray  # pint Quantity array
    error_diffusion_constant: np.ndarray


class RadiusOfGyrationResults(TypedDict):
    """Type definition for radius of gyration calculation results."""

    times: np.ndarray  # pint Quantity array (or plain array if no time units)
    value: np.ndarray  # pint Quantity array in angstrom
    n_frames: int


class MolecularRadiusOfGyrationResults(TypedDict):
    """Type definition for molecular radius of gyration results with metadata."""

    times: np.ndarray  # pint Quantity array (or plain array if no time units)
    value: np.ndarray  # pint Quantity array in angstrom
    n_frames: int
    label: str  # molecule label with index
    system_ref: Any  # reference to the molecule section


# Module-level constants for molecular dynamics calculations
MAX_MOLECULES_PERFORMANCE_WARNING = (
    50000  # Threshold for performance warning in MSD calculations
)


def _log_missing_dependency(dependency: str, calculation: str) -> str:
    """
    Generates a standardized warning message for missing dependencies.

    Args:
        dependency: The required dependency (e.g., 'universe', 'bead_groups')
        calculation: The calculation being attempted (e.g., 'RDF', 'MSD', 'radius of gyration')

    Returns:
        A formatted warning message string
    """
    return f'{dependency} required to calculate {calculation}.'


def _check_package_dependency(
    package_name: str, function_name: str, extras_name: str = 'md'
) -> bool:
    """
    Checks if a required package is available and logs an error if not.

    Args:
        package_name: The name of the package (e.g., 'MDAnalysis', 'networkx')
        function_name: The name of the function requiring the package
        extras_name: The extras group to install (default: 'md')

    Returns:
        True if the package is available, False otherwise
    """
    is_available = False
    if package_name.lower() == 'mdanalysis':
        is_available = _HAS_MDA
    elif package_name.lower() == 'networkx':
        is_available = _HAS_NETWORKX

    if not is_available:
        LOGGER.error(
            f'{function_name} requires {package_name}. '
            f'Please install with `pip install nomad-simulations[{extras_name}]`.'
        )
        return False
    return True


class BeadGroup:
    """A helper class for calculating properties of groups of atoms ("beads") with the MDAnalysis package.
    See https://github.com/MDAnalysis/mdanalysis/issues/1891#issuecomment-387138110 by @richardjgowers with performance improvements.

    Args:
        object (MDAnalysis.AtomGroup): complete set of atoms for consideration.

    Returns:
        bead_groups: returns  bead group object that links and subdivides the MDAnalysis.AtomGroup, when attributes are requested.
    """

    def __init__(self, atoms, compound='fragments'):
        """Initialize with an AtomGroup instance.
        Will split based on keyword 'compounds' (residues or fragments).

        self._atoms: AtomGroup (total number of atoms)
        self.compound: str (dictates type of grouping)
        self._nbeads: int (total number of beads)
        self.positions: list (total number of "compounds")
        """
        self._atoms = atoms
        self.compound = compound
        self._nbeads = len(getattr(self._atoms, self.compound))
        # for caching
        self._cache = {}
        self._cache['positions'] = None
        self.__last_frame = None

    def __len__(self):
        return self._nbeads

    @property
    def positions(self):
        # cache positions for current frame
        if self.universe.trajectory.frame != self.__last_frame:
            self._cache['positions'] = (
                self._atoms.center_of_mass(unwrap=True, compound=self.compound)
                if self._nbeads != 0
                else []
            )
            self.__last_frame = self.universe.trajectory.frame
        return self._cache['positions']

    @property
    # @property  # type: ignore  # COMMENTED OUT: Decorator fails when MDAnalysis is not installed
    # @MDAnalysis.lib.util.cached('universe')  # TODO: Test if this caching decorator is necessary for performance
    def universe(self):
        # Manual caching implementation to replace MDAnalysis decorator
        if 'universe' not in self._cache:
            self._cache['universe'] = self._atoms.universe
        return self._cache['universe']


def get_bond_list_from_model_contributions(
    sec_method,
) -> list[tuple]:
    """
    Extracts a list of bonds from the ForceField.contributions in the provided method
    section.
    Returns:
        bond_list: List[tuple]
    """
    bond_list: list[tuple[int, ...]] = []
    if sec_method is None:
        return bond_list
    contributions = getattr(sec_method, 'contributions', None)
    if contributions is None or len(contributions) == 0:
        return bond_list
    for contribution in contributions:
        pi = getattr(contribution, 'particle_indices', None)
        if (
            pi is None
            or not isinstance(pi, np.ndarray)
            or pi.ndim != 2
            or pi.shape[1] != 2
        ):
            continue
        bond_list.extend([tuple(indices) for indices in pi])
    return bond_list


def create_empty_universe(
    n_atoms: int,
    n_frames: int = 1,
    n_residues: int = 1,
    n_segments: int = 1,
    atom_resindex: np.ndarray | None = None,
    residue_segindex: np.ndarray | None = None,
    flag_trajectory: bool = False,
    flag_velocities: bool = False,
    flag_forces: bool = False,
    timestep: float | None = None,
) -> MDAUniverse | None:
    """Create a blank Universe

    This function was adapted from the function empty() within the MDA class Universe().
    The only difference is that the Universe() class is imported directly here, whereas in the
    original function is passed as a function argument, since the function there is a class method.

    Useful for building a Universe without requiring existing files,
    for example for system building.

    If `flag_trajectory` is set to True, a
    :class:`MDAnalysis.coordinates.memory.MemoryReader` will be
    attached to the Universe.

    Parameters
    ----------
    n_atoms: int
      number of Atoms in the Universe
    n_residues: int, default 1
      number of Residues in the Universe, defaults to 1
    n_segments: int, default 1
      number of Segments in the Universe, defaults to 1
    atom_resindex: array like, optional
      mapping of atoms to residues, e.g. with 6 atoms,
      `atom_resindex=[0, 0, 1, 1, 2, 2]` would put 2 atoms
      into each of 3 residues.
    residue_segindex: array like, optional
      mapping of residues to segments
    flag_trajectory: bool, optional
      if True, attaches a :class:`MDAnalysis.coordinates.memory.MemoryReader`
      allowing coordinates to be set and written.  Default is False
    flag_velocities: bool, optional
      include velocities in the :class:`MDAnalysis.coordinates.memory.MemoryReader`
    flag_forces: bool, optional
      include forces in the :class:`MDAnalysis.coordinates.memory.MemoryReader`

    Returns
    -------
    MDAnalysis.Universe object

    Examples
    --------
    For example to create a new Universe with 6 atoms in 2 residues, with
    positions for the atoms and a mass attribute:

    >>> u = mda.Universe.empty(6, 2,
                                atom_resindex=np.array([0, 0, 0, 1, 1, 1]),
                                flag_trajectory=True,
            )
    >>> u.add_TopologyAttr('masses')

    .. versionadded:: 0.17.0
    .. versionchanged:: 0.19.0
        The attached Reader when flag_trajectory=True is now a MemoryReader
    .. versionchanged:: 1.0.0
        Universes can now be created with 0 atoms
    """
    if not _check_package_dependency('MDAnalysis', 'create_empty_universe', 'md'):
        return None

    if not n_atoms:
        n_residues = 0
        n_segments = 0

    if atom_resindex is None:
        LOGGER.warning(
            'Residues specified but no atom_resindex given.  '
            'All atoms will be placed in first Residue.',
        )

    if residue_segindex is None:
        LOGGER.warning(
            'Segments specified but no residue_segindex given.  '
            'All residues will be placed in first Segment',
        )

    topology = Topology(
        n_atoms,
        n_residues,
        n_segments,
        atom_resindex=atom_resindex,
        residue_segindex=residue_segindex,
    )

    universe = Universe(topology)

    if flag_trajectory:
        coords = np.zeros((n_frames, n_atoms, 3), dtype=np.float32)
        vels = np.zeros_like(coords) if flag_velocities else None
        forces = np.zeros_like(coords) if flag_forces else None

        # grab and attach a MemoryReader
        universe.trajectory = get_reader_for(coords)(
            coords,
            order='fac',
            n_atoms=n_atoms,
            velocities=vels,
            forces=forces,
            dt=timestep,
        )

    return universe


def archive_to_universe(
    archive,
    system_index: int = 0,  # TODO: Shouldn't this be -1 (representative_system)
    method_index: int = -1,
    model_index: int = -1,
) -> MDAUniverse | None:
    """Extract the topology from a provided run section of an archive entry

    Input:

        archive: EntryArchive
    Variables:

        n_frames (int):

        n_atoms (int):

        atom_names (str, shape=(n_atoms)):

        atom_types (str, shape=(n_atoms)):

        atom_resindex (str, shape=(n_atoms)):

        atom_segids (str, shape=(n_atoms)):

        n_segments (int): Segments correspond to a group of the same type of molecules.

        n_residues (int): The number of distinct residues (nb - individual molecules are also denoted as a residue).

        resnames (str, shape=(n_residues)): The name of each residue.

        residue_segindex (int, shape=(n_residues)): The segment index that each residue belongs to.

        residue_molnums (int, shape=(n_residues)): The molecule index that each residue belongs to.

        residue_moltypes (int, shape=(n_residues)): The molecule type of each residue.

        n_molecules (int):

        masses (float, shape=(n_atoms)):  atom masses, units = amu

        charges (float, shape=(n_atoms)): atom partial charges, units = e

        positions (float, shape=(n_frames,n_atoms,3)): atom positions

        velocities (float, shape=(n_frames,n_atoms,3)): atom velocities

        dimensions (float, shape=(n_frames,6)): box dimensions (nb - currently assuming a cubic box!)

        bonds (tuple, shape=([])): list of tuples with the atom indices of each bond
    """
    if not _check_package_dependency('MDAnalysis', 'archive_to_universe', 'md'):
        return None

    if archive.data:
        try:
            data = archive.data
            sec_system = data.model_system
            sec_system_top = sec_system[system_index]
            sec_atoms_group = (
                sec_system_top.sub_systems if sec_system_top is not None else None
            )
            sec_method = data.model_method[method_index] if data.model_method else None

        except Exception:
            LOGGER.warning('Archive can not be read.')
            return None
    else:
        LOGGER.warning(
            'No data section found in archive. Cannot build the MDA universe.'
        )
        return None

    n_atoms = sec_system_top.get('n_particles') if sec_system is not None else None
    if n_atoms is None:
        LOGGER.warning('No atoms found in the archive. Cannot build the MDA universe.')
        return None
    particle_states = sec_system_top.particle_states if sec_system is not None else None
    atom_names = [ps.label for ps in particle_states] if particle_states else None
    atom_types = [ps.chemical_symbol for ps in particle_states]
    _ppc = (
        next(
            (
                ns
                for ns in (sec_method.numerical_settings or [])
                if isinstance(ns, ParticleParametersContainer)
            ),
            None,
        )
        if sec_method is not None
        else None
    )

    _pp_by_label: dict[str, Any] = {}

    if _ppc is not None:
        for pp in _ppc.particle_parameters or []:
            if pp.particle_type is not None:
                _pp_by_label[pp.particle_type] = pp

    _masses_list: list[Any] = []
    _charges_list: list[Any] = []
    for ps in particle_states:
        pp = _pp_by_label.get(ps.label)
        if ps.mass is not None:
            _masses_list.append(
                ureg.convert(ps.mass.magnitude, ps.mass.units, ureg.amu)
            )
        elif pp is not None and pp.effective_mass is not None:
            _masses_list.append(
                ureg.convert(
                    pp.effective_mass.magnitude, pp.effective_mass.units, ureg.amu
                )
            )
        else:
            LOGGER.warning(
                'Missing mass for atom %s. Using default value from ASE.',
                ps.chemical_symbol,
            )
            _masses_list.append(
                ase.data.atomic_masses[
                    ase.data.atomic_numbers.get(ps.chemical_symbol, 0)
                ]
            )
        if pp is not None and pp.partial_charge is not None:
            _charges_list.append(
                ureg.convert(
                    pp.partial_charge.magnitude, pp.partial_charge.units, ureg.e
                )
            )
        else:
            # TODO: is this the best way to handle missing charges?
            LOGGER.warning(
                'Missing charge for atom %s. Using default value 0.0.',
                ps.chemical_symbol,
            )
            _charges_list.append(0.0)

    masses = np.array(_masses_list)
    charges = np.array(_charges_list)

    system_times = [
        t
        for out in (archive.data.outputs or [])
        if (t := getattr(out, 'time', None)) is not None
    ]
    n_frames = len(sec_system)

    atom_resindex = np.arange(n_atoms)
    atoms_segindices = np.empty(n_atoms)
    atom_segids = np.array(range(n_atoms), dtype='object')
    molecule_groups = sec_atoms_group
    n_segments = len(molecule_groups)

    # Attribute accessors for archive.run / archive.data backward compatibility.
    def _atom_idx(obj):
        return obj.particle_indices

    def _label(obj):
        return obj.name if obj.name is not None else obj.branch_label

    def _sub_objs(obj):
        subs = obj.sub_systems
        return subs if subs is not None else []

    n_residues = 0
    n_molecules = 0
    residue_segindex = []
    resnames = []
    residue_moltypes = []
    residue_min_atom_index = []
    residue_n_atoms = []
    molecule_n_res = []
    for mol_group_ind, mol_group in enumerate(molecule_groups):
        atoms_segindices[_atom_idx(mol_group)] = mol_group_ind
        atom_segids[_atom_idx(mol_group)] = _label(mol_group)
        molecules = _sub_objs(mol_group)
        for mol in molecules:
            monomer_groups = _sub_objs(mol)
            mol_res_counter = 0
            if monomer_groups:
                for mon_group in monomer_groups:
                    monomers = _sub_objs(mon_group)
                    for mon in monomers:
                        resnames.append(_label(mon))
                        residue_segindex.append(mol_group_ind)
                        residue_moltypes.append(_label(mol))
                        residue_min_atom_index.append(np.min(_atom_idx(mon)))
                        residue_n_atoms.append(len(_atom_idx(mon)))
                        n_residues += 1
                        mol_res_counter += 1
            else:  # no monomers => whole molecule is its own residue
                resnames.append(_label(mol))
                residue_segindex.append(mol_group_ind)
                residue_moltypes.append(_label(mol))
                residue_min_atom_index.append(np.min(_atom_idx(mol)))
                residue_n_atoms.append(len(_atom_idx(mol)))
                n_residues += 1
                mol_res_counter += 1
            molecule_n_res.append(mol_res_counter)
            n_molecules += 1

    # reorder the residues by atom_indices
    residue_data = np.array(
        [
            [
                residue_min_atom_index[i],
                residue_n_atoms[i],
                residue_segindex[i],
                residue_moltypes[i],
                resnames[i],
            ]
            for i in range(len(residue_min_atom_index))
        ],
        dtype=object,
    )
    residue_data = np.array(sorted(residue_data, key=lambda x: x[0], reverse=False)).T
    residue_n_atoms = residue_data[1].astype(int)
    residue_segindex = residue_data[2].astype(int)
    residue_moltypes = residue_data[3]
    resnames = residue_data[4]
    res_index_counter = 0
    for i_residue, res_n_atoms in enumerate(residue_n_atoms):
        atom_resindex[res_index_counter : res_index_counter + res_n_atoms] = i_residue  # type: ignore
        res_index_counter += res_n_atoms
    residue_molnums = np.array(range(n_residues))
    mol_index_counter = 0
    for i_molecule, n_res in enumerate(molecule_n_res):
        residue_molnums[mol_index_counter : mol_index_counter + n_res] = i_molecule
        mol_index_counter += n_res

    # get the atom positions, velocities, and box dimensions
    positions = np.empty(shape=(n_frames, n_atoms, 3))
    dimensions = np.empty(shape=(n_frames, 6))
    has_velocities = any(frame.velocities is not None for frame in sec_system)
    velocities = np.zeros(shape=(n_frames, n_atoms, 3)) if has_velocities else None
    for frame_ind, frame in enumerate(sec_system):
        positions_frame = frame.positions
        velocities_frame = frame.velocities
        latt_vec_tmp = frame.lattice_vectors
        if positions_frame is not None:
            positions[frame_ind] = ureg.convert(
                positions_frame.magnitude, positions_frame.units, ureg.angstrom
            )
        if has_velocities and velocities_frame is not None:
            velocities[frame_ind] = ureg.convert(
                velocities_frame.magnitude,
                velocities_frame.units,
                ureg.angstrom / ureg.picosecond,
            )
        if latt_vec_tmp is not None:
            length_conversion = ureg.convert(1.0, latt_vec_tmp.units, ureg.angstrom)
            dimensions[frame_ind] = [
                latt_vec_tmp.magnitude[0][0] * length_conversion,
                latt_vec_tmp.magnitude[1][1] * length_conversion,
                latt_vec_tmp.magnitude[2][2] * length_conversion,
                90,
                90,
                90,
            ]  # TODO: extend to non-cubic boxes

    # get the bonds  # TODO extend to multiple storage options for interactions
    bonds = (
        [tuple(bond) for bond in getattr(sec_system_top, 'bond_list', None) or []]
        if sec_system_top is not None
        else None
    )
    if bonds is None:
        bonds = get_bond_list_from_model_contributions(sec_method)

    # get the system times
    system_timestep = 1.0 * ureg.picosecond

    def approx(a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    if system_times:
        time_steps = [
            system_times[i_time] - system_times[i_time - 1]
            for i_time in range(1, len(system_times))
        ]
        if all(approx(time_steps[0], time_step) for time_step in time_steps):
            system_timestep = (
                ureg.convert(
                    time_steps[0].magnitude, time_steps[0].units, ureg.picosecond
                )
                * ureg.picosecond
            )
        else:
            LOGGER.warning(
                'System times are not equally spaced. Cannot set system times in MDA '
                'universe. MDA universe will contain non-physical times and timestep.'
            )
    else:
        try:
            method = archive.workflow2.method
            dt = method.integration_timestep
            freq = method.coordinate_save_frequency
            if dt is not None:
                system_timestep = dt * freq if freq is not None else dt
            else:
                raise ValueError('integration_timestep is None')
        except Exception:
            LOGGER.warning(
                'Cannot find the system times. MDA universe will contain non-physical '
                'times and timestep.'
            )

    if not hasattr(system_timestep, 'to'):
        system_timestep = system_timestep * ureg.picosecond
    else:
        system_timestep = system_timestep.to(ureg.picosecond)

    # create the Universe
    metainfo_universe = create_empty_universe(
        n_atoms,
        n_frames=n_frames,
        n_residues=n_residues,
        n_segments=n_segments,
        atom_resindex=np.array(atom_resindex),
        residue_segindex=np.array(residue_segindex),
        flag_trajectory=True,
        flag_velocities=has_velocities,
        timestep=system_timestep.magnitude,
    )

    # set the positions and velocities
    for frame_ind, frame in enumerate(metainfo_universe.trajectory):
        metainfo_universe.atoms.positions = positions[frame_ind]
        if has_velocities:
            metainfo_universe.atoms.velocities = velocities[frame_ind]

    # add the atom attributes
    metainfo_universe.add_TopologyAttr('name', atom_names)
    metainfo_universe.add_TopologyAttr('type', atom_types)
    metainfo_universe.add_TopologyAttr('mass', masses)
    metainfo_universe.add_TopologyAttr('charge', charges)
    if n_segments != 0:
        segids = [_label(mol_group) for mol_group in molecule_groups]
        metainfo_universe.add_TopologyAttr('segids', segids)
    if n_residues != 0:
        metainfo_universe.add_TopologyAttr('resnames', resnames)
        metainfo_universe.add_TopologyAttr('resids', np.arange(n_residues) + 1)
        metainfo_universe.add_TopologyAttr('resnums', np.arange(n_residues) + 1)
    if len(residue_molnums) > 0:
        metainfo_universe.add_TopologyAttr('molnums', residue_molnums)
    if len(residue_moltypes) > 0:
        metainfo_universe.add_TopologyAttr('moltypes', residue_moltypes)

    # add the box dimensions
    for frame_ind, frame in enumerate(metainfo_universe.trajectory):
        metainfo_universe.atoms.dimensions = dimensions[frame_ind]

    # add the bonds
    if bonds is not None:
        if hasattr(metainfo_universe, 'bonds'):
            LOGGER.warning('archive_to_universe() failed, universe already has bonds.')
            return None
        metainfo_universe.add_TopologyAttr('bonds', bonds)

    return metainfo_universe


def _get_molecular_bead_groups(
    universe: MDAUniverse | None, moltypes: list[str] = []
) -> dict[str, BeadGroup]:
    """
    Creates bead groups based on the molecular types as defined by the MDAnalysis
    universe.
    """
    if not _check_package_dependency('MDAnalysis', '_get_molecular_bead_groups', 'md'):
        return {}

    # Input validation
    if universe is None:
        LOGGER.warning(_log_missing_dependency('universe', 'beads'))
        return {}

    if not moltypes:
        atoms_moltypes = getattr(universe.atoms, 'moltypes', [])
        moltypes = np.unique(atoms_moltypes).tolist()
    bead_groups = {}
    for moltype in moltypes:
        ags_by_moltype = universe.select_atoms('moltype ' + moltype)
        if ags_by_moltype.n_atoms == 0:
            continue

        if ags_by_moltype.masses is not None:
            ags_by_moltype = ags_by_moltype[
                ags_by_moltype.masses > abs(1e-2)
            ]  # remove any virtual/massless sites (needed for, e.g., 4-bead water models)
        bead_groups[moltype] = BeadGroup(ags_by_moltype, compound='fragments')

    return bead_groups


def calc_molecular_rdf(
    universe: MDAUniverse | None,
    bead_groups: dict[str, BeadGroup],
    n_traj_split: int = 10,
    n_prune: int = 1,
    interval_indices=None,
    max_mols: int = 5000,
) -> MolecularRDFResults | dict[str, Any]:
    """
    Calculates the radial distribution functions between for each unique pair of
    molecule types as a function of their center of mass distance.

    Parameters
    ----------
    universe : MDAnalysis.Universe
        The MDAnalysis universe object.
    bead_groups : dict[str, BeadGroup]
        Precomputed bead groups for the universe.
    n_traj_split : int
        Number of intervals to split trajectory into for averaging.
    n_prune : int
        Pruning parameter for frames.
    interval_indices : list or None
        2D array specifying the groups of the n_traj_split intervals to be averaged.
    max_mols : int
        Maximum number of molecules per bead group for calculating the rdf, for efficiency purposes.
    """
    if not _check_package_dependency('MDAnalysis', 'calc_molecular_rdf', 'md'):
        return {}

    # TODO 5k default for max_mols was set after > 50k was giving problems. Should do further testing to see where the appropriate limit should be set.
    if bead_groups is None or not bead_groups:
        LOGGER.warning(_log_missing_dependency('bead_groups', 'RDF'))
        return {}

    if (
        not universe
        or not universe.trajectory
        or universe.trajectory[0].dimensions is None
    ):
        LOGGER.warning(_log_missing_dependency('universe', 'RDF'))
        return {}

    n_frames = universe.trajectory.n_frames
    if n_frames < n_traj_split:
        n_traj_split = 1
        frames_start = np.array([0])
        frames_end = np.array([n_frames])
        n_frames_split = np.array([n_frames])
        interval_indices = [[0]]
    else:
        run_len = int(n_frames / n_traj_split)
        frames_start = np.arange(n_traj_split) * run_len
        frames_end = frames_start + run_len
        frames_end[-1] = n_frames
        n_frames_split = frames_end - frames_start
        if np.sum(n_frames_split) != n_frames:
            LOGGER.error(
                'Something went wrong with input parameters in calc_molecular_rdf().'
                'Radial distribution functions will not be calculated.'
            )
            return {}
        if not interval_indices:
            interval_indices = [[i] for i in range(n_traj_split)]

    if not bead_groups:
        return bead_groups
    moltypes = list(bead_groups.keys())
    del_list = [
        i_moltype
        for i_moltype, moltype in enumerate(moltypes)
        if len(bead_groups[moltype].positions) > max_mols
    ]
    moltypes = np.delete(moltypes, del_list).tolist()

    min_box_dimension = np.min(universe.trajectory[0].dimensions[:3])
    max_rdf_dist = min_box_dimension / 2
    n_bins = 200
    n_smooth = 2

    rdf_results: dict[str, Any] = {}
    rdf_results['n_smooth'] = n_smooth
    rdf_results['n_prune'] = n_prune
    rdf_results['type'] = 'molecular'
    rdf_results['types'] = []
    rdf_results['variables_name'] = []
    rdf_results['bins'] = []
    rdf_results['value'] = []
    rdf_results['frame_start'] = []
    rdf_results['frame_end'] = []
    for i, moltype_i in enumerate(moltypes):
        for j, moltype_j in enumerate(moltypes):
            if j > i:
                continue
            elif (
                i == j and bead_groups[moltype_i].positions.shape[0] == 1
            ):  # skip if only 1 mol in group
                continue

            if i == j:
                exclusion_block = (1, 1)  # remove self-distance
            else:
                exclusion_block = None
            pair_type = f'{moltype_i}-{moltype_j}'
            rdf_results_interval: dict[str, Any] = {}
            rdf_results_interval['types'] = []
            rdf_results_interval['variables_name'] = []
            rdf_results_interval['bins'] = []
            rdf_results_interval['value'] = []
            rdf_results_interval['frame_start'] = []
            rdf_results_interval['frame_end'] = []
            for i_interval in range(n_traj_split):
                rdf_results_interval['types'].append(pair_type)
                rdf_results_interval['variables_name'].append(['distance'])
                rdf = MDA_RDF.InterRDF(
                    bead_groups[moltype_i],
                    bead_groups[moltype_j],
                    range=(0, max_rdf_dist),
                    exclusion_block=exclusion_block,
                    nbins=n_bins,
                ).run(frames_start[i_interval], frames_end[i_interval], n_prune)
                rdf_results_interval['frame_start'].append(frames_start[i_interval])
                rdf_results_interval['frame_end'].append(frames_end[i_interval])

                rdf_results_interval['bins'].append(
                    rdf.results.bins[int(n_smooth / 2) : -int(n_smooth / 2)]
                    * ureg.angstrom
                )
                rdf_results_interval['value'].append(
                    np.convolve(
                        rdf.results.rdf, np.ones((n_smooth,)) / n_smooth, mode='same'
                    )[int(n_smooth / 2) : -int(n_smooth / 2)]
                )

            flag_logging_error = False
            for interval_group in interval_indices:
                split_weights = n_frames_split[np.array(interval_group)] / np.sum(
                    n_frames_split[np.array(interval_group)]
                )
                if abs(np.sum(split_weights) - 1.0) > 1e-6:
                    flag_logging_error = True
                    continue
                rdf_values_avg = (
                    split_weights[0] * rdf_results_interval['value'][interval_group[0]]
                )
                for i_interval, interval in enumerate(interval_group[1:]):
                    if (
                        rdf_results_interval['types'][interval]
                        != rdf_results_interval['types'][interval - 1]
                    ):
                        flag_logging_error = True
                        continue
                    if (
                        rdf_results_interval['variables_name'][interval]
                        != rdf_results_interval['variables_name'][interval - 1]
                    ):
                        flag_logging_error = True
                        continue
                    if not (
                        rdf_results_interval['bins'][interval]
                        == rdf_results_interval['bins'][interval - 1]
                    ).all():
                        flag_logging_error = True
                        continue
                    rdf_values_avg += (
                        split_weights[i_interval + 1]
                        * rdf_results_interval['value'][interval]
                    )
                if flag_logging_error:
                    LOGGER.error(
                        'Something went wrong in calc_molecular_rdf(). Some interval groups were skipped.'
                    )
                rdf_results['types'].append(
                    rdf_results_interval['types'][interval_group[0]]
                )
                rdf_results['variables_name'].append(
                    rdf_results_interval['variables_name'][interval_group[0]]
                )
                rdf_results['bins'].append(
                    rdf_results_interval['bins'][interval_group[0]]
                )
                rdf_results['value'].append(rdf_values_avg)
                rdf_results['frame_start'].append(
                    int(rdf_results_interval['frame_start'][interval_group[0]])
                )
                rdf_results['frame_end'].append(
                    int(rdf_results_interval['frame_end'][interval_group[-1]])
                )

    return rdf_results


def _log_indices(first: int, last: int, num: int = 100):
    ls = np.logspace(0, np.log10(last - first + 1), num=num)
    return np.unique(np.int_(ls) - 1 + first)


def _correlation(function, positions: list[float]):
    iterator = iter(positions)
    start_frame = next(iterator)
    return map(lambda f: function(start_frame, f), chain([start_frame], iterator))


def _linear_fit(x_data: np.ndarray, y_data: np.ndarray) -> tuple[float, float]:
    """
    Performs a linear regression fit on the provided data.

    Args:
        x_data: Independent variable data (e.g., time values)
        y_data: Dependent variable data (e.g., mean squared displacement)

    Returns:
        tuple: (slope, r_value) where slope is the fitted slope and r_value is the
               Pearson correlation coefficient indicating quality of fit
    """
    linear_model = linregress(x_data, y_data)
    slope = linear_model.slope
    r_value = linear_model.rvalue
    return slope, r_value


def shifted_correlation_average(
    function: Callable,
    times: np.ndarray,
    positions: np.ndarray,
    index_distribution: Callable = _log_indices,
    correlation: Callable = _correlation,
    segments: int = 10,
    window: float = 0.5,
    skip: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Code adapted from MDevaluate module: https://github.com/mdevaluate/mdevaluate.git

    Calculate the time series for a correlation function.

    The times at which the correlation is calculated are determined automatically by the
    function given as ``index_distribution``. The default is a logarithmic distribution.

    The function has been edited so that the average is always calculated, i.e., average=True below.

    Args:
        function:   The function that should be correlated
        positions:     The coordinates of the simulation data
        index_distribution (opt.):
                    A function that returns the indices for which the timeseries
                    will be calculated
        correlation (function, opt.):
                    The correlation function
        segments (int, opt.):
                    The number of segments the time window will be shifted
        window (float, opt.):
                    The fraction of the simulation the time series will cover
        skip (float, opt.):
                    The fraction of the trajectory that will be skipped at the beginning,
                    if this is None the start index of the frames slice will be used,
                    which defaults to 0.
        counter (bool, opt.):
                    If True, returns length of frames (in general number of particles specified)
        average (bool, opt.):
                    If True,
    Returns:
        tuple:
            A list of length N that contains the indices of the frames at which
            the time series was calculated and a numpy array of shape (segments, N)
            that holds the (non-averaged) correlation data

            if has_counter == True: adds number of counts to output tuple.
                                    if average is returned it will be weighted.

    Example:
        Calculating the mean square displacement of a coordinates object named ``coords``:

        >>> indices, data = shifted_correlation(msd, coords)
    """
    if window + skip >= 1:
        LOGGER.warning(
            'Invalid parameters for shifted_correlation(), resetting to defaults.',
        )
        window = 0.5
        skip = 0

    start_frames = np.unique(
        np.linspace(
            len(positions) * skip,
            len(positions) * (1 - window),
            num=segments,
            endpoint=False,
            dtype=int,
        )
    )
    num_frames = int(len(positions) * (window))

    idx = index_distribution(0, num_frames)

    def correlate(start_frame):
        shifted_idx = idx + start_frame
        return correlation(function, map(positions.__getitem__, shifted_idx))

    correlation_times = np.array([times[i] for i in idx]) - times[0]

    result: np.ndarray
    for i_start_frame, start_frame in enumerate(start_frames):
        if i_start_frame == 0:
            result = np.array(list(correlate(start_frame)))
        else:
            result += np.array(list(correlate(start_frame)))
    result = np.array(result)
    result = result / len(start_frames)

    return correlation_times, result


def calc_molecular_msd(
    universe: MDAUniverse | None,
    bead_groups: dict[str, BeadGroup],
    max_mols: int = 5000,
) -> MolecularMSDResults | dict[str, Any]:
    """
    Calculates the mean squared displacement for the center of mass of each
    molecule type.

    Parameters
    ----------
    universe : MDAnalysis.Universe
        The MDAnalysis universe object.
    bead_groups : dict[str, BeadGroup]
        Precomputed bead groups for the universe.
    max_mols : int
        Maximum number of molecules per bead group for calculating the msd, for efficiency purposes.
    """
    if not _check_package_dependency('MDAnalysis', 'calc_molecular_msd', 'md'):
        return {}

    def parse_jumps(universe, selection):  # TODO Add output declaration
        """
        See __get_nojump_positions().
        """
        __ = universe.trajectory[0]
        prev = np.array(selection.positions)
        box = universe.trajectory[0].dimensions[:3]
        sparse_data = namedtuple('SparseData', ['data', 'row', 'col'])  # type: ignore[name-match]
        jump_data = (
            sparse_data(data=array('b'), row=array('l'), col=array('l')),
            sparse_data(data=array('b'), row=array('l'), col=array('l')),
            sparse_data(data=array('b'), row=array('l'), col=array('l')),
        )

        for i_frame, _ in enumerate(universe.trajectory[1:]):
            curr = np.array(selection.positions)
            delta = ((curr - prev) / box).round().astype(np.int8)
            prev = np.array(curr)
            for d in range(3):
                (col,) = np.where(delta[:, d] != 0)
                jump_data[d].col.extend(col)
                jump_data[d].row.extend([i_frame] * len(col))
                jump_data[d].data.extend(delta[col, d])

        return jump_data

    def generate_nojump_matrices(universe, selection):  # TODO Add output declaration
        """
        See __get_nojump_positions().
        """
        jump_data = parse_jumps(universe, selection)
        n_frames = len(universe.trajectory)
        n_atoms = selection.positions.shape[0]

        nojump_matrices = tuple(
            sparse.csr_matrix(
                (np.array(m.data), (m.row, m.col)), shape=(n_frames, n_atoms)
            )
            for m in jump_data
        )
        return nojump_matrices

    def get_nojump_positions(universe, selection) -> np.ndarray:
        """
        Unwraps the positions to create a continuous trajectory without jumps across periodic boundaries.
        """
        nojump_matrices = generate_nojump_matrices(universe, selection)
        box = universe.trajectory[0].dimensions[:3]

        nojump_positions = []
        for i_frame, __ in enumerate(universe.trajectory):
            delta = (
                np.array(
                    np.vstack([m[:i_frame, :].sum(axis=0) for m in nojump_matrices]).T
                )
                * box
            )
            nojump_positions.append(selection.positions - delta)

        return np.array(nojump_positions)

    def mean_squared_displacement(start: np.ndarray, current: np.ndarray) -> float:
        """
        Calculates mean square displacement between current and initial (start) coordinates.
        """
        vec = start - current
        return (vec**2).sum(axis=1).mean()

    if not bead_groups:
        LOGGER.warning(_log_missing_dependency('bead_groups', 'MSD'))
        return {}

    if (
        not universe
        or not universe.trajectory
        or universe.trajectory[0].dimensions is None
    ):
        LOGGER.warning(_log_missing_dependency('universe', 'MSD'))
        return {}

    n_frames = universe.trajectory.n_frames
    if n_frames < 50:
        LOGGER.warning(
            'At least 50 frames required to calculate molecular'
            ' mean squared displacements, skipping.',
        )
        return {}

    # TODO universe.trajectory.dt?
    dt = getattr(universe.trajectory, 'dt')
    if dt is None:
        LOGGER.warning(
            'Universe is missing time step, cannot calculate molecular'
            ' mean squared displacements, skipping.',
        )
        return {}
    times = np.arange(n_frames) * dt

    if bead_groups == {}:
        return bead_groups

    moltypes = [moltype for moltype in bead_groups.keys()]
    del_list = []
    has_large_groups = False
    has_errors = False

    if max_mols > MAX_MOLECULES_PERFORMANCE_WARNING:
        LOGGER.warning(
            f'Calculating mean squared displacements for more than {MAX_MOLECULES_PERFORMANCE_WARNING} molecules.'
            ' Expect long processing times!',
        )

    for i_moltype, moltype in enumerate(moltypes):
        if len(bead_groups[moltype].positions) > max_mols:
            has_large_groups = True
            try:
                # select max_mols nr. of rnd molecules from this moltype
                moltype_indices = np.array(
                    [atom._ix for atom in bead_groups[moltype]._atoms]
                )
                molnums = universe.atoms.molnums[moltype_indices]
                molnum_types = np.unique(molnums)
                molnum_types_rnd = np.sort(
                    np.random.choice(molnum_types, size=max_mols)
                )
                atom_indices_rnd = np.concatenate(
                    [moltype_indices[molnums == molnum] for molnum in molnum_types_rnd]
                )
                selection = ' '.join([str(i) for i in atom_indices_rnd])
                selection = f'index {selection}'
                ags_moltype_rnd = universe.select_atoms(selection)
                bead_groups[moltype] = BeadGroup(ags_moltype_rnd, compound='fragments')
            except Exception:
                has_errors = True
                del_list.append(i_moltype)

    for index in sorted(del_list, reverse=True):
        del moltypes[index]

    if has_large_groups:
        LOGGER.warning(
            'Maximum number of molecules for calculating the msd has been reached.'
            ' Random selection used for calculation.'
        )
    if has_errors:
        LOGGER.warning(
            'Error in selecting random molecules for large group when calculating msd.'
            ' Some molecule types were skipped.'
        )

    msd_results: dict[str, Any] = {
        'type': 'molecular',
        'direction': 'xyz',
        'value': [],
        'times': [],
        'diffusion_constant': [],
        'error_diffusion_constant': [],
    }
    for moltype in moltypes:
        positions = get_nojump_positions(universe, bead_groups[moltype])
        results = shifted_correlation_average(
            mean_squared_displacement, times, positions
        )
        if results:
            msd_results['value'].append(results[1])
            msd_results['times'].append(results[0])
            slope, r_value = _linear_fit(*results)
            # Calculate diffusion constant from slope using Einstein relation: D = slope / (2 * dim)
            diffusion_constant = slope * 1 / (2 * 3)  # dim=3 for 3D diffusion
            msd_results['diffusion_constant'].append(diffusion_constant)
            msd_results['error_diffusion_constant'].append(r_value)

    msd_results['types'] = moltypes
    msd_results['times'] = np.array(msd_results['times']) * ureg.picosecond
    msd_results['value'] = np.array(msd_results['value']) * ureg.angstrom**2
    msd_results['diffusion_constant'] = (
        np.array(msd_results['diffusion_constant']) * ureg.angstrom**2 / ureg.picosecond
    )
    msd_results['error_diffusion_constant'] = np.array(
        msd_results['error_diffusion_constant']
    )

    return msd_results


def calc_radius_of_gyration(
    universe: MDAUniverse | None, molecule_particle_indices: np.ndarray
) -> RadiusOfGyrationResults | dict[str, Any]:
    """
    Calculates the radius of gyration as a function of time for the particles 'molecule_particle_indices'.

    molecule_particle_indices : np.ndarray
        The indices of the particles corresponding to a single molecule for which the Rg will be calculated.
    """
    if not _check_package_dependency('MDAnalysis', 'calc_radius_of_gyration', 'md'):
        return {}

    if molecule_particle_indices is None or len(molecule_particle_indices) == 0:
        LOGGER.warning(
            _log_missing_dependency('molecule_particle_indices', 'radius of gyration')
        )
        return {}

    if (
        not universe
        or not universe.trajectory
        or universe.trajectory[0].dimensions is None
    ):
        LOGGER.warning(_log_missing_dependency('universe', 'radius of gyration'))
        return {}
    selection = ' '.join([str(i) for i in molecule_particle_indices])
    selection = f'index {selection}'
    molecule = universe.select_atoms(selection)
    rg_results: dict[str, Any] = {}
    rg_results['times'] = []
    rg_results['value'] = []
    time_unit = getattr(universe.trajectory.time, 'units', None)
    for __ in universe.trajectory:
        rg_results['times'].append(
            universe.trajectory.time.magnitude
            if time_unit
            else universe.trajectory.time
        )
        rg_results['value'].append(molecule.radius_of_gyration())
    rg_results['n_frames'] = len(rg_results['times'])
    rg_results['times'] = (
        np.array(rg_results['times']) * time_unit
        if time_unit
        else np.array(rg_results['times'])
    )
    rg_results['value'] = np.array(rg_results['value']) * ureg.angstrom

    return rg_results


def calc_molecular_rg(
    universe: MDAUniverse | None, system_hierarchy: MSection
) -> list[dict[str, Any]]:
    """
    Calculates the radius of gyration as a function of time for each polymer in the system.

    Returns a list of dictionaries containing RadiusOfGyrationResults data plus
    additional metadata (label, system_ref).
    """
    if not _check_package_dependency('MDAnalysis', 'calc_molecular_rg', 'md'):
        return []

    if universe is None:
        LOGGER.warning(
            _log_missing_dependency('universe', 'molecular radius of gyration')
        )
        return []
    if system_hierarchy is None or not system_hierarchy:
        LOGGER.warning(
            _log_missing_dependency('system_topology', 'molecular radius of gyration')
        )
        return []

    rg_results: list[dict[str, Any]] = []
    for molgroup in system_hierarchy:
        for i_mol, molecule in enumerate(molgroup.sub_systems or []):
            sec_monomer_groups = molecule.sub_systems
            group_type = (
                sec_monomer_groups[0].branch_label if sec_monomer_groups else None
            )
            if (
                group_type != 'monomer_group'
            ):  # TODO need a better way to identify polymers
                continue
            rg_result = calc_radius_of_gyration(universe, molecule.particle_indices)
            # Convert TypedDict to regular dict and add metadata
            result_dict: dict[str, Any] = dict(rg_result)
            result_dict['label'] = (
                (molecule.name if molecule.name is not None else molecule.branch_label)
                + '-index_'
                + str(i_mol)
            )
            result_dict['system_ref'] = molecule
            rg_results.append(result_dict)

    return rg_results


def get_molecules_from_bond_list(
    n_particles: int,
    bond_list: list[tuple],
    particle_types: list[str] = [],
    particles_typeid: array | None = None,
) -> list[dict[str, Any]]:
    """
    Returns a list of dictionaries with molecule info from each instance in the list of bonds.
    """
    if not _check_package_dependency('networkx', 'get_molecules_from_bond_list', 'md'):
        return []

    system_graph = networkx.empty_graph(n_particles)
    system_graph.add_edges_from([(i[0], i[1]) for i in bond_list])
    molecules = [
        system_graph.subgraph(c).copy()
        for c in networkx.connected_components(system_graph)
    ]
    molecule_info: list[dict[str, Any]] = []
    for mol in molecules:
        molecule_dict: dict[str, Any] = {}
        molecule_dict['indices'] = np.array(mol.nodes())
        molecule_dict['bonds'] = np.array(mol.edges())
        molecule_dict['type'] = 'molecule'
        molecule_dict['is_molecule'] = True
        if particles_typeid is None and len(particle_types) == n_particles:
            molecule_dict['names'] = [
                particle_types[int(x)]
                for x in sorted(np.array(molecule_dict['indices']))
            ]
        if particle_types is not None and particles_typeid is not None:
            molecule_dict['names'] = [
                particle_types[particles_typeid[int(x)]]
                for x in sorted(np.array(molecule_dict['indices']))
            ]
        molecule_info.append(molecule_dict)
    return molecule_info


def _is_same_molecule(mol_1: dict, mol_2: dict) -> bool:
    """
    Checks whether the 2 input molecule dictionary (see "get_molecules_from_bond_list()" above)
    represent the same molecule type, i.e., same particle types and corresponding bond connections.
    """

    def get_bond_list_dict(mol):
        mol_shift = np.min(mol['indices'])
        mol_bonds_shift = mol['bonds'] - mol_shift
        bond_list = [
            sorted((mol['names'][i], mol['names'][j])) for i, j in mol_bonds_shift
        ]
        bond_list_names, bond_list_counts = np.unique(
            bond_list, axis=0, return_counts=True
        )

        return {
            bond[0] + '-' + bond[1]: bond_list_counts[i_bond]
            for i_bond, bond in enumerate(bond_list_names)
        }

    if sorted(mol_1['names']) != sorted(mol_2['names']):
        return False

    bond_list_dict_1 = get_bond_list_dict(mol_1)
    bond_list_dict_2 = get_bond_list_dict(mol_2)

    return bond_list_dict_1 == bond_list_dict_2


def model_system_to_universe(system: ModelSystem, logger=None) -> MDAUniverse | None:
    """Returns an instance of mda.Universe from a NOMAD Atoms-section.

    Args:
        system: The atoms to transform
        logger: Optional logger (currently unused)

    Returns:
        A new mda.Universe created from the given data.
    """
    if not _check_package_dependency('MDAnalysis', 'model_system_to_universe', 'md'):
        return None

    n_atoms = len(system.positions)
    n_residues = 1
    atom_resindex = [0] * n_atoms
    residue_segindex = [0]

    universe = MDAnalysis.Universe.empty(
        n_atoms,
        n_residues=n_residues,
        atom_resindex=atom_resindex,
        residue_segindex=residue_segindex,
        trajectory=True,
    )

    # Add positions
    universe.atoms.positions = system.positions.to(ureg.angstrom).magnitude

    # Add atom attributes
    atom_names = system.labels
    universe.add_TopologyAttr('name', atom_names)
    universe.add_TopologyAttr('type', atom_names)
    universe.add_TopologyAttr('element', atom_names)

    # Add the box dimensions
    if system.lattice_vectors is not None:
        universe.atoms.dimensions = atomutils.cell_to_cellpar(
            system.lattice_vectors.to(ureg.angstrom).magnitude, degrees=True
        )

    return universe
