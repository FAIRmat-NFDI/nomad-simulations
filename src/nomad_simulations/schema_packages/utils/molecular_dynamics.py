from __future__ import annotations

from array import array
from collections import namedtuple
from collections.abc import Callable
from itertools import chain
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy import sparse
from scipy.stats import linregress

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


def _check_mda_dependency(function_name: str) -> bool:
    """
    Checks if MDAnalysis is available and logs an error if not.

    Args:
        function_name: The name of the function requiring MDAnalysis

    Returns:
        True if MDAnalysis is available, False otherwise
    """
    if not _HAS_MDA:
        LOGGER.error(
            f'{function_name} requires MDAnalysis. '
            'Please install with `pip install nomad-simulations[md]`.'
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

    @property  # type: ignore
    @MDAnalysis.lib.util.cached('universe')
    def universe(self):
        return self._atoms.universe


# TODO update from runschema to nomad-simulations
# def get_bond_list_from_model_contributions(
#     sec_run: MSection, method_index: int = -1, model_index: int = -1
# ) -> list[tuple]:
#     """
#     Generates bond list of tuples using the list of bonded force field interactions stored under run[].method[].force_field.model[].

#     bond_list: List[tuple]
#     """
#     contributions = []
#     if sec_run.m_xpath(
#         f'method[{method_index}].force_field.model[{model_index}].contributions'
#     ):
#         contributions = (
#             sec_run.method[method_index].force_field.model[model_index].contributions
#         )
#     bond_list = []
#     for contribution in contributions:
#         if contribution.type != 'bond':
#             continue

#         atom_indices = contribution.atom_indices
#         if (
#             contribution.n_interactions
#         ):  # all bonds have been grouped into one contribution
#             bond_list = [tuple(indices) for indices in atom_indices]
#         else:
#             bond_list.append(tuple(contribution.atom_indices))

#     return bond_list


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
    if not _check_mda_dependency('create_empty_universe'):
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


TODO: update run to data
def archive_to_universe(
    archive,
    system_index: int = 0,
    method_index: int = -1,
    model_index: int = -1,
) -> MDAUniverse | None:
    """Extract the topology from a provided run section of an archive entry

    Input:

        archive_sec_run: section run of an EntryArchive

        system_index: list index of archive.run[].system to be used for topology extraction

        method_index: list index of archive.run[].method to be used for atom parameter (charges and masses) extraction

        model_index: list index of archive.run[].method[].force_field.model for bond list extraction

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
    if not _check_mda_dependency('archive_to_universe'):
        return None

    # TODO just return None until we convert to data
    return None
#     try:
#         sec_run = archive.run[-1]
#         sec_system = sec_run.system
#         sec_system_top = sec_run.system[system_index]
#         sec_atoms = sec_system_top.atoms
#         sec_atoms_group = sec_system_top.atoms_group
#         sec_calculation = sec_run.calculation
#         sec_method = (
#             sec_run.method[method_index] if sec_run.get('method') is not None else {}
#         )
#     except IndexError:
#         LOGGER.warning(
#             'Supplied indices or necessary sections do not exist in archive. Cannot build the MDA universe.'
#         )
#         return None

#     n_atoms = sec_atoms.get('n_atoms')
#     if n_atoms is None:
#         LOGGER.warning('No atoms found in the archive. Cannot build the MDA universe.')
#         return None

#     n_frames = len(sec_system) if sec_system is not None else 1
#     atom_names = sec_atoms.get('labels')
#     model_atom_parameters = sec_method.get('atom_parameters')
#     atom_types = (
#         [atom.label for atom in model_atom_parameters]
#         if model_atom_parameters
#         else atom_names
#     )
#     atom_resindex = np.arange(n_atoms)
#     atoms_segindices = np.empty(n_atoms)
#     atom_segids = np.array(range(n_atoms), dtype='object')
#     molecule_groups = sec_atoms_group
#     n_segments = len(molecule_groups)

#     n_residues = 0
#     n_molecules = 0
#     residue_segindex = []
#     resnames = []
#     residue_moltypes = []
#     residue_min_atom_index = []
#     residue_n_atoms = []
#     molecule_n_res = []
#     for mol_group_ind, mol_group in enumerate(molecule_groups):
#         atoms_segindices[mol_group.atom_indices] = mol_group_ind
#         atom_segids[mol_group.atom_indices] = mol_group.label
#         molecules = mol_group.atoms_group if mol_group.atoms_group is not None else []
#         for mol in molecules:
#             monomer_groups = mol.atoms_group
#             mol_res_counter = 0
#             if monomer_groups:
#                 for mon_group in monomer_groups:
#                     monomers = mon_group.atoms_group
#                     for mon in monomers:
#                         resnames.append(mon.label)
#                         residue_segindex.append(mol_group_ind)
#                         residue_moltypes.append(mol.label)
#                         residue_min_atom_index.append(np.min(mon.atom_indices))
#                         residue_n_atoms.append(len(mon.atom_indices))
#                         n_residues += 1
#                         mol_res_counter += 1
#             else:  # no monomers => whole molecule is it's own residue
#                 resnames.append(mol.label)
#                 residue_segindex.append(mol_group_ind)
#                 residue_moltypes.append(mol.label)
#                 residue_min_atom_index.append(np.min(mol.atom_indices))
#                 residue_n_atoms.append(len(mol.atom_indices))
#                 n_residues += 1
#                 mol_res_counter += 1
#             molecule_n_res.append(mol_res_counter)
#             n_molecules += 1

#     # reorder the residues by atom_indices
#     residue_data = np.array(
#         [
#             [
#                 residue_min_atom_index[i],
#                 residue_n_atoms[i],
#                 residue_segindex[i],
#                 residue_moltypes[i],
#                 resnames[i],
#             ]
#             for i in range(len(residue_min_atom_index))
#         ],
#         dtype=object,
#     )
#     residue_data = np.array(sorted(residue_data, key=lambda x: x[0], reverse=False)).T
#     residue_n_atoms = residue_data[1].astype(int)
#     residue_segindex = residue_data[2].astype(int)
#     residue_moltypes = residue_data[3]
#     resnames = residue_data[4]
#     res_index_counter = 0
#     for i_residue, res_n_atoms in enumerate(residue_n_atoms):
#         atom_resindex[res_index_counter : res_index_counter + res_n_atoms] = i_residue  # type: ignore
#         res_index_counter += res_n_atoms
#     residue_molnums = np.array(range(n_residues))
#     mol_index_counter = 0
#     for i_molecule, n_res in enumerate(molecule_n_res):
#         residue_molnums[mol_index_counter : mol_index_counter + n_res] = i_molecule
#         mol_index_counter += n_res

#     # get the atom masses and charges

#     masses = np.empty(n_atoms)
#     charges = np.empty(n_atoms)
#     atom_parameters = (
#         sec_method.get('atom_parameters') if sec_method is not None else []
#     )
#     atom_parameters = atom_parameters if atom_parameters is not None else []

#     for atom_ind, atom in enumerate(atom_parameters):
#         if atom.get('mass'):
#             masses[atom_ind] = ureg.convert(
#                 atom.mass.magnitude, atom.mass.units, ureg.amu
#             )
#         if atom.get('charge'):
#             charges[atom_ind] = ureg.convert(
#                 atom.charge.magnitude, atom.charge.units, ureg.e
#             )

#     # get the atom positions, velocities, and box dimensions
#     positions = np.empty(shape=(n_frames, n_atoms, 3))
#     velocities = np.empty(shape=(n_frames, n_atoms, 3))
#     dimensions = np.empty(shape=(n_frames, 6))
#     for frame_ind, frame in enumerate(sec_system):
#         sec_atoms_fr = frame.get('atoms')
#         if sec_atoms_fr is not None:
#             positions_frame = sec_atoms_fr.positions
#             positions[frame_ind] = (
#                 ureg.convert(
#                     positions_frame.magnitude, positions_frame.units, ureg.angstrom
#                 )
#                 if positions_frame is not None
#                 else None
#             )
#             velocities_frame = sec_atoms_fr.velocities
#             velocities[frame_ind] = (
#                 ureg.convert(
#                     velocities_frame.magnitude,
#                     velocities_frame.units,
#                     ureg.angstrom / ureg.picosecond,
#                 )
#                 if velocities_frame is not None
#                 else None
#             )
#             latt_vec_tmp = sec_atoms_fr.get('lattice_vectors')
#             if latt_vec_tmp is not None:
#                 length_conversion = ureg.convert(
#                     1.0, sec_atoms_fr.lattice_vectors.units, ureg.angstrom
#                 )
#                 dimensions[frame_ind] = [
#                     sec_atoms_fr.lattice_vectors.magnitude[0][0] * length_conversion,
#                     sec_atoms_fr.lattice_vectors.magnitude[1][1] * length_conversion,
#                     sec_atoms_fr.lattice_vectors.magnitude[2][2] * length_conversion,
#                     90,
#                     90,
#                     90,
#                 ]  # TODO: extend to non-cubic boxes

#     # get the bonds  # TODO extend to multiple storage options for interactions
#     bonds = sec_atoms.bond_list
#     # TODO add back in once get_bond_list_from_model_contributions is updated
#     # if bonds is None:
#     #     bonds = get_bond_list_from_model_contributions(
#     #         sec_run, method_index=-1, model_index=-1
#     #     )

#     # get the system times
#     system_timestep = 1.0 * ureg.picosecond

#     def approx(a, b, rel_tol=1e-09, abs_tol=0.0):
#         return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

#     system_times = [calc.time for calc in sec_calculation if calc.system_ref]
#     if system_times:
#         try:
#             method = archive.workflow2.method
#             system_timestep = (
#                 method.integration_timestep * method.coordinate_save_frequency
#             )
#         except Exception:
#             LOGGER.warning(
#                 'Cannot find the system times. MDA universe will contain non-physical times and timestep.'
#             )
#     else:
#         time_steps = [
#             system_times[i_time] - system_times[i_time - 1]
#             for i_time in range(1, len(system_times))
#         ]
#         if all(approx(time_steps[0], time_step) for time_step in time_steps):
#             system_timestep = ureg.convert(
#                 time_steps[0].magnitude, ureg.second, ureg.picosecond
#             )
#         else:
#             LOGGER.warning(
#                 'System times are not equally spaced. Cannot set system times in MDA universe.'
#                 ' MDA universe will contain non-physical times and timestep.'
#             )

#     system_timestep = ureg.convert(
#         system_timestep, system_timestep._units, ureg.picoseconds
#     )

#     # create the Universe
#     metainfo_universe = create_empty_universe(
#         n_atoms,
#         n_frames=n_frames,
#         n_residues=n_residues,
#         n_segments=n_segments,
#         atom_resindex=np.array(atom_resindex),
#         residue_segindex=np.array(residue_segindex),
#         flag_trajectory=True,
#         flag_velocities=True,
#         timestep=system_timestep.magnitude,
#     )

#     # set the positions and velocities
#     for frame_ind, frame in enumerate(metainfo_universe.trajectory):
#         metainfo_universe.atoms.positions = positions[frame_ind]
#         metainfo_universe.atoms.velocities = velocities[frame_ind]

#     # add the atom attributes
#     metainfo_universe.add_TopologyAttr('name', atom_names)
#     metainfo_universe.add_TopologyAttr('type', atom_types)
#     metainfo_universe.add_TopologyAttr('mass', masses)
#     metainfo_universe.add_TopologyAttr('charge', charges)
#     if n_segments != 0:
#         metainfo_universe.add_TopologyAttr('segids', np.unique(atom_segids))
#     if n_residues != 0:
#         metainfo_universe.add_TopologyAttr('resnames', resnames)
#         metainfo_universe.add_TopologyAttr('resids', np.unique(atom_resindex) + 1)
#         metainfo_universe.add_TopologyAttr('resnums', np.unique(atom_resindex) + 1)
#     if len(residue_molnums) > 0:
#         metainfo_universe.add_TopologyAttr('molnums', residue_molnums)
#     if len(residue_moltypes) > 0:
#         metainfo_universe.add_TopologyAttr('moltypes', residue_moltypes)

#     # add the box dimensions
#     for frame_ind, frame in enumerate(metainfo_universe.trajectory):
#         metainfo_universe.atoms.dimensions = dimensions[frame_ind]

#     # add the bonds
#     if hasattr(metainfo_universe, 'bonds'):
#         LOGGER.warning('archive_to_universe() failed, universe already has bonds.')
#         return None
#     metainfo_universe.add_TopologyAttr('bonds', bonds)

#     return metainfo_universe


def _get_molecular_bead_groups(
    universe: MDAUniverse | None, moltypes: list[str] = []
) -> dict[str, BeadGroup]:
    """
    Creates bead groups based on the molecular types as defined by the MDAnalysis universe.
    """
    if not _check_mda_dependency('_get_molecular_bead_groups'):
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
) -> dict[str, Any]:
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
    if not _check_mda_dependency('calc_molecular_rdf'):
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


def _calc_diffusion_constant(
    times: np.ndarray, values: np.ndarray, dim: int = 3
) -> tuple[float, float]:
    """
    Determines the diffusion constant from a fit of the mean squared displacement
    vs. time according to the Einstein relation.
    """
    linear_model = linregress(times, values)
    slope = linear_model.slope
    error = linear_model.rvalue
    return slope * 1 / (2 * dim), error


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


def calc_molecular_mean_squared_displacements(
    universe: MDAUniverse | None,
    bead_groups: dict[str, BeadGroup],
    max_mols: int = 5000,
) -> dict[str, Any]:
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
    if not _check_mda_dependency('calc_molecular_mean_squared_displacements'):
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

    def mean_squared_displacement(start: np.ndarray, current: np.ndarray):
        """
        Calculates mean square displacement between current and initial (start) coordinates.
        """
        vec = start - current
        return (vec**2).sum(axis=1).mean()

    if bead_groups is None or not bead_groups:
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
    for i_moltype, moltype in enumerate(moltypes):
        if len(bead_groups[moltype].positions) > max_mols:
            if max_mols > 50000:
                LOGGER.warning(
                    'Calculating mean squared displacements for more than 50k molecules.'
                    ' Expect long processing times!',
                )
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
                LOGGER.warning(
                    'Maximum number of molecules for calculating the msd has been reached.'
                    ' Will make a random selection for calculation.'
                )
            except Exception:
                LOGGER.warning(
                    'Error in selecting random molecules for large group when calculating msd. Skipping this molecule type.'
                )
                del_list.append(i_moltype)

    for index in sorted(del_list, reverse=True):
        del moltypes[index]

    msd_results: dict[str, Any] = {}
    msd_results['type'] = 'molecular'
    msd_results['direction'] = 'xyz'
    msd_results['value'] = []
    msd_results['times'] = []
    msd_results['diffusion_constant'] = []
    msd_results['error_diffusion_constant'] = []
    for moltype in moltypes:
        positions = get_nojump_positions(universe, bead_groups[moltype])
        results = shifted_correlation_average(
            mean_squared_displacement, times, positions
        )
        if results:
            msd_results['value'].append(results[1])
            msd_results['times'].append(results[0])
            diffusion_constant, error = _calc_diffusion_constant(*results)
            msd_results['diffusion_constant'].append(diffusion_constant)
            msd_results['error_diffusion_constant'].append(error)

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
) -> dict[str, Any]:
    """
    Calculates the radius of gyration as a function of time for the particles 'molecule_particle_indices'.

    molecule_particle_indices : np.ndarray
        The indices of the particles corresponding to a single molecule for which the Rg will be calculated.
    """
    if not _check_mda_dependency('calc_radius_of_gyration'):
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


def calc_molecular_radius_of_gyration(
    universe: MDAUniverse | None, system_hierarchy: MSection
) -> list[dict[str, Any]]:
    """
    Calculates the radius of gyration as a function of time for each polymer in the system.
    """
    if not _check_mda_dependency('calc_molecular_radius_of_gyration'):
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

    rg_results = []
    for molgroup in system_hierarchy:
        for i_mol, molecule in enumerate(molgroup.subsystems):
            sec_monomer_groups = molecule.subsystems
            group_type = (
                sec_monomer_groups[0].branch_label if sec_monomer_groups else None
            )
            if (
                group_type != 'monomer_group'
            ):  # TODO need a better way to identify polymers
                continue
            rg_result = calc_radius_of_gyration(universe, molecule.particle_indices)
            rg_result['label'] = molecule.label + '-index_' + str(i_mol)
            rg_result['system_ref'] = molecule
            rg_results.append(rg_result)

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
    if not _HAS_NETWORKX:
        LOGGER.error(
            'get_molecules_from_bond_list requires networkx. '
            'Please install with `pip install nomad-simulations[md]`.'
        )
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
    if not _check_mda_dependency('model_system_to_universe'):
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
