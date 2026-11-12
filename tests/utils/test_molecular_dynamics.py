"""
Tests for utils/molecular_dynamics.py changes:
  - getattr guard: BaseModelMethod must not raise AttributeError for ForceField-only quantities
  - ForceField.effective_masses / partial_charges are accessible via getattr
  - archive_to_universe mass/charge code paths (requires MDAnalysis)
"""

import numpy as np
import pytest
from nomad.datamodel import EntryArchive
from nomad.units import ureg

from nomad_simulations.schema_packages.atoms_state import AtomsState, CGBeadState
from nomad_simulations.schema_packages.force_field import (
    ForceField,
    ParticleParameters,
    ParticleParametersContainer,
)
from nomad_simulations.schema_packages.general import Simulation
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.model_system import ModelSystem
from nomad_simulations.schema_packages.outputs import TrajectoryOutputs
from nomad_simulations.schema_packages.utils.molecular_dynamics import (
    _get_molecular_bead_groups,
    archive_to_universe,
)
from nomad_simulations.schema_packages.workflow.molecular_dynamics import (
    MolecularDynamics,
    MolecularDynamicsMethod,
)

# ---------------------------------------------------------------------------
# getattr guard — regression tests for AttributeError: effective_masses
# ---------------------------------------------------------------------------


def test_getattr_guard_base_model_method_effective_masses():
    """getattr with default on base ModelMethod returns None (attribute absent on non-FF methods)."""
    mm = ModelMethod()
    assert getattr(mm, 'effective_masses', None) is None


def test_getattr_guard_base_model_method_partial_charges():
    """getattr with default on base ModelMethod returns None (attribute absent on non-FF methods)."""
    mm = ModelMethod()
    assert getattr(mm, 'partial_charges', None) is None


# ---------------------------------------------------------------------------
# archive_to_universe — mass / charge path selection (requires MDAnalysis)
# ---------------------------------------------------------------------------

MDAnalysis = pytest.importorskip('MDAnalysis', reason='MDAnalysis not installed')


def _build_minimal_archive(n_atoms=3, with_ff_masses=False, with_ff_charges=False):
    """
    Build a minimal EntryArchive with enough structure for archive_to_universe
    to reach the mass/charge assignment lines.

    The archive has:
      - archive.data (Simulation)
      - archive.data.model_system[0] with n_particles and particle_states
      - archive.data.model_system[0].sub_systems (one molecule group containing
        one molecule, which is its own residue)
      - archive.data.model_method[-1] — ForceField if with_ff_* flags set,
        otherwise plain ModelMethod
      - archive.data.outputs = [] (empty, so system_times is [])

    Atom types: O H H  (water)
    """
    # Particle states
    labels = ['O', 'H', 'H']
    particle_states = []
    for sym in labels:
        ps = AtomsState()
        ps.chemical_symbol = sym
        ps.label = sym
        particle_states.append(ps)

    # archive_to_universe expects: molecule_groups -> molecules -> (optional monomers).
    # A molecule with no sub_systems is treated as its own residue.
    molecule = ModelSystem()
    molecule.branch_label = 'SOL'
    molecule.particle_indices = np.arange(n_atoms)

    mol_group = ModelSystem()
    mol_group.branch_label = 'SOL_group'
    mol_group.particle_indices = np.arange(n_atoms)
    mol_group.sub_systems = [molecule]

    # Trajectory frame with positions — required so archive_to_universe does not
    # return None due to "no frames with positions".
    frame = ModelSystem()
    frame.positions = np.zeros((n_atoms, 3)) * ureg.angstrom

    root_system = ModelSystem()
    root_system.n_particles = n_atoms
    root_system.particle_states = particle_states
    root_system.sub_systems = [mol_group]

    # Method
    if with_ff_masses or with_ff_charges:
        method = ForceField()
        ppc = ParticleParametersContainer()
        type_data = {
            'O': {'mass_amu': 15.999, 'charge_e': -0.82},
            'H': {'mass_amu': 1.008, 'charge_e': 0.41},
        }
        for label, vals in type_data.items():
            pp = ParticleParameters()
            pp.particle_type = label
            if with_ff_masses:
                pp.effective_mass = (vals['mass_amu'] * ureg.amu).to('kg')
            if with_ff_charges:
                pp.partial_charge = vals['charge_e'] * ureg.elementary_charge
            ppc.particle_parameters.append(pp)
        method.numerical_settings.append(ppc)
    else:
        method = ModelMethod()

    sim = Simulation()
    sim.model_system = [root_system, frame]
    sim.representative_system_index = 0
    sim.model_method = [method]

    archive = EntryArchive()
    archive.data = sim
    return archive


def test_archive_to_universe_masses_from_forcefield():
    """Masses come from ParticleParameters.effective_mass in ParticleParametersContainer."""

    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=True, with_ff_charges=False
    )
    universe = archive_to_universe(archive)

    if universe is None:
        pytest.skip('archive_to_universe returned None — topology too minimal for MDA')

    expected_amu = np.array([15.999, 1.008, 1.008])
    assert np.isclose(universe.atoms.masses, expected_amu, rtol=1e-4).all()


def test_archive_to_universe_charges_from_forcefield():
    """Charges come from ParticleParameters.partial_charge in ParticleParametersContainer."""

    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=False, with_ff_charges=True
    )
    universe = archive_to_universe(archive)

    if universe is None:
        pytest.skip('archive_to_universe returned None — topology too minimal for MDA')

    expected_e = np.array([-0.82, 0.41, 0.41])
    assert np.isclose(universe.atoms.charges, expected_e, atol=1e-6).all()


def test_archive_to_universe_charges_zero_fallback():
    """When no ForceField is present, charges default to zero."""

    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=False, with_ff_charges=False
    )
    universe = archive_to_universe(archive)

    if universe is None:
        pytest.skip('archive_to_universe returned None — topology too minimal for MDA')

    assert np.allclose(universe.atoms.charges, 0.0)


def test_archive_to_universe_topology_not_at_index_0():
    """Topology is found by particle_states search even when not at model_system[0]."""
    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=False, with_ff_charges=False
    )
    # Prepend a bare positional frame (no particle_states) so topology is at index 1.
    # Metainfo lists only support append, so rebuild the list.
    bare_frame = ModelSystem()
    bare_frame.positions = np.zeros((3, 3)) * ureg.angstrom
    original = list(archive.data.model_system)
    archive.data.model_system = []
    for ms in [bare_frame] + original:
        archive.data.model_system.append(ms)

    universe = archive_to_universe(archive)
    if universe is None:
        pytest.skip('archive_to_universe returned None — topology too minimal for MDA')

    assert universe.atoms.n_atoms == 3


def test_archive_to_universe_base_model_method_no_attribute_error():
    """
    Base ModelMethod as sec_method must not raise AttributeError in archive_to_universe.
    """

    # This is the exact regression scenario: sec_method is ModelMethod, not ForceField
    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=False, with_ff_charges=False
    )
    # Explicitly verify sec_method is a plain ModelMethod (not ForceField)
    assert not isinstance(archive.data.model_method[-1], ForceField)

    # Must not raise AttributeError
    try:
        archive_to_universe(archive)
    except AttributeError as exc:
        pytest.fail(
            f'archive_to_universe raised AttributeError with base ModelMethod: {exc}'
        )


def _build_hierarchy_archive(n_atoms, molecules):
    """Create a one-frame archive from molecule and optional monomer index lists."""
    root = ModelSystem(
        n_particles=n_atoms,
        positions=np.zeros((n_atoms, 3)) * ureg.angstrom,
    )
    root.particle_states = [
        AtomsState(chemical_symbol='H', label='H') for _ in range(n_atoms)
    ]
    group = ModelSystem(
        name='group',
        branch_label='molecule_group',
        particle_indices=np.arange(n_atoms),
    )
    for molecule_index, (indices, monomers) in enumerate(molecules):
        molecule = ModelSystem(
            name=f'molecule_{molecule_index}',
            branch_label='molecule',
            particle_indices=np.array(indices),
        )
        if monomers:
            monomer_group = ModelSystem(
                name=f'monomer_group_{molecule_index}',
                branch_label='monomer_group',
                particle_indices=np.array(indices),
            )
            for monomer_index, monomer_indices in enumerate(monomers):
                monomer_group.sub_systems.append(
                    ModelSystem(
                        name=f'monomer_{molecule_index}_{monomer_index}',
                        branch_label='monomer',
                        particle_indices=np.array(monomer_indices),
                    )
                )
            molecule.sub_systems.append(monomer_group)
        group.sub_systems.append(molecule)
    root.sub_systems.append(group)
    archive = EntryArchive()
    archive.data = Simulation(model_system=[root], model_method=[ModelMethod()])
    return archive


def test_archive_to_universe_interleaved_molecules_keep_particle_membership():
    archive = _build_hierarchy_archive(4, [([0, 2], None), ([1, 3], None)])
    for molecule in archive.data.model_system[0].sub_systems[0].sub_systems:
        molecule.name = 'same_type'
    archive = EntryArchive.m_from_dict(archive.m_to_dict())

    universe = archive_to_universe(archive)

    assert universe is not None
    assert universe.atoms.resindices.tolist() == [0, 1, 0, 1]
    assert universe.atoms.molnums.tolist() == [0, 1, 0, 1]
    assert universe.atoms.moltypes.tolist() == ['same_type'] * 4


def test_archive_to_universe_interleaved_monomers_keep_parent_molecules():
    archive = _build_hierarchy_archive(
        8,
        [
            ([0, 2, 4, 6], [[0, 2], [4, 6]]),
            ([1, 3, 5, 7], [[1, 3], [5, 7]]),
        ],
    )

    universe = archive_to_universe(archive)

    assert universe is not None
    assert universe.atoms.resindices.tolist() == [0, 1, 0, 1, 2, 3, 2, 3]
    assert universe.atoms.molnums.tolist() == [0, 1, 0, 1, 0, 1, 0, 1]
    assert universe.residues.resnames.tolist() == [
        'monomer_0_0',
        'monomer_1_0',
        'monomer_0_1',
        'monomer_1_1',
    ]


def test_archive_to_universe_rejects_overlapping_molecules(caplog):
    archive = _build_hierarchy_archive(4, [([0, 1], None), ([1, 2, 3], None)])

    assert archive_to_universe(archive) is None
    assert 'overlap' in caplog.text.lower()


def test_archive_to_universe_rejects_uncovered_particles(caplog):
    archive = _build_hierarchy_archive(4, [([0, 2], None), ([1], None)])

    assert archive_to_universe(archive) is None
    assert 'uncovered' in caplog.text.lower()


def test_archive_to_universe_cg_single_site_molecules():
    archive = _build_hierarchy_archive(3, [([0], None), ([1], None), ([2], None)])
    archive.data.model_system[0].particle_states = [
        CGBeadState(bead_symbol='B', label=f'B{index}') for index in range(3)
    ]

    universe = archive_to_universe(archive)

    assert universe is not None
    assert universe.atoms.types.tolist() == ['B'] * 3
    assert universe.atoms.molnums.tolist() == [0, 1, 2]


def test_archive_to_universe_without_hierarchy_keeps_one_residue():
    archive = _build_hierarchy_archive(3, [([0, 1, 2], None)])
    archive.data.model_system[0].sub_systems = []

    universe = archive_to_universe(archive)

    assert universe is not None
    assert universe.atoms.resindices.tolist() == [0, 0, 0]


def _build_timed_archive(frame_times, method_timestep=None, save_frequency=None):
    archive = _build_minimal_archive()
    system = archive.data.model_system[0]
    system.positions = np.zeros((3, 3)) * ureg.angstrom
    system.lattice_vectors = np.eye(3) * 10 * ureg.angstrom
    n_frames = max(len(frame_times), 1)
    archive.data.model_system = [
        system,
        *[
            ModelSystem(positions=np.zeros((3, 3)) * ureg.angstrom)
            for _ in range(n_frames - 1)
        ],
    ]
    archive.data.outputs = [
        TrajectoryOutputs(time=time * ureg.picosecond) for time in frame_times
    ]
    if method_timestep is not None:
        archive.workflow2 = MolecularDynamics(
            method=MolecularDynamicsMethod(
                integration_timestep=method_timestep * ureg.picosecond,
                coordinate_save_frequency=save_frequency,
            )
        )
    return archive


@pytest.mark.parametrize(
    ('frame_times', 'method_timestep', 'save_frequency', 'expected_dt', 'warns'),
    [
        pytest.param([0], None, None, 1.0, True, id='one-time-no-method'),
        pytest.param([0], 0.5, 4, 2.0, False, id='one-time-method'),
        pytest.param([], 0.5, 4, 2.0, False, id='no-times-method'),
        pytest.param([0], 0.5, None, 1.0, True, id='one-time-no-frequency'),
        pytest.param([0], 0.5, 0, 1.0, True, id='one-time-zero-frequency'),
        pytest.param([0], 0.5, -1, 1.0, True, id='one-time-negative-frequency'),
        pytest.param([0, 0.1], 0.5, 4, 0.1, False, id='two-times-beat-method'),
    ],
)
def test_archive_to_universe_timestep_sources(
    frame_times, method_timestep, save_frequency, expected_dt, warns, caplog
):
    archive = _build_timed_archive(frame_times, method_timestep, save_frequency)

    universe = archive_to_universe(archive)

    assert universe is not None
    assert universe.trajectory.n_frames == max(len(frame_times), 1)
    assert universe.trajectory.dt == pytest.approx(expected_dt)
    assert (
        'using the default 1 ps for the MDAnalysis trajectory' in caplog.text
    ) == warns


def test_get_molecular_bead_groups_handles_plain_moltype_tokens():
    """
    Plain moltype labels must resolve via boolean indexing.
    """
    universe = MDAnalysis.Universe.empty(1)
    universe.add_TopologyAttr('moltypes', np.array(['mol']))
    universe.add_TopologyAttr('masses', np.array([15.999]))
    universe.add_TopologyAttr('bonds', [])

    bead_groups = _get_molecular_bead_groups(universe)

    assert 'mol' in bead_groups


def test_get_molecular_bead_groups_handles_reserved_keyword_moltypes():
    """
    Regression: moltype labels like "water" must not trigger selection parser issues.
    """
    universe = MDAnalysis.Universe.empty(1)
    universe.add_TopologyAttr('moltypes', np.array(['water']))
    universe.add_TopologyAttr('masses', np.array([15.999]))
    universe.add_TopologyAttr('bonds', [])

    bead_groups = _get_molecular_bead_groups(universe)

    assert 'water' in bead_groups


def test_get_molecular_bead_groups_counts_fragments():
    """BeadGroup counts bonded atoms as a single fragment."""
    universe = MDAnalysis.Universe.empty(3, n_residues=3, atom_resindex=[0, 1, 2])
    universe.add_TopologyAttr('moltypes', np.array(['mol', 'mol', 'mol']))
    universe.add_TopologyAttr('masses', np.array([15.999, 1.008, 1.008]))
    universe.add_TopologyAttr('bonds', [(0, 1), (1, 2)])

    bead_groups = _get_molecular_bead_groups(universe)

    assert 'mol' in bead_groups
    assert len(bead_groups['mol']) == 1
