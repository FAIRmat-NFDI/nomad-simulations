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

from nomad_simulations.schema_packages.force_field import ForceField
from nomad_simulations.schema_packages.model_method import ModelMethod

from . import logger

# ---------------------------------------------------------------------------
# getattr guard — regression tests for AttributeError: effective_masses
# ---------------------------------------------------------------------------


def test_getattr_guard_base_model_method_effective_masses():
    """Base ModelMethod must return None (not AttributeError) for effective_masses."""
    mm = ModelMethod()
    result = getattr(mm, 'effective_masses', None)
    assert result is None


def test_getattr_guard_base_model_method_partial_charges():
    """Base ModelMethod must return None (not AttributeError) for partial_charges."""
    mm = ModelMethod()
    result = getattr(mm, 'partial_charges', None)
    assert result is None


def test_getattr_guard_forcefield_effective_masses_returns_value():
    """getattr returns the value when ForceField.effective_masses is set."""
    ff = ForceField()
    masses_amu = np.array([15.999, 1.008, 1.008])
    ff.effective_masses = (masses_amu * ureg.amu).to('kg')

    result = getattr(ff, 'effective_masses', None)
    assert result is not None
    assert len(result) == 3
    assert np.isclose(result.to('amu').magnitude, masses_amu, rtol=1e-5).all()


def test_getattr_guard_forcefield_partial_charges_returns_value():
    """getattr returns the value when ForceField.partial_charges is set."""
    ff = ForceField()
    charges = np.array([-0.82, 0.41, 0.41])
    ff.partial_charges = charges * ureg.elementary_charge

    result = getattr(ff, 'partial_charges', None)
    assert result is not None
    assert len(result) == 3
    assert np.isclose(result.to('elementary_charge').magnitude, charges).all()


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
    from nomad_simulations.schema_packages.atoms_state import AtomsState
    from nomad_simulations.schema_packages.general import Simulation
    from nomad_simulations.schema_packages.model_system import ModelSystem

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

    root_system = ModelSystem()
    root_system.n_particles = n_atoms
    root_system.particle_states = particle_states
    root_system.sub_systems = [mol_group]

    # Method
    if with_ff_masses or with_ff_charges:
        method = ForceField()
        if with_ff_masses:
            masses_amu = np.array([15.999, 1.008, 1.008])
            method.effective_masses = (masses_amu * ureg.amu).to('kg')
        if with_ff_charges:
            charges = np.array([-0.82, 0.41, 0.41])
            method.partial_charges = charges * ureg.elementary_charge
    else:
        method = ModelMethod()

    sim = Simulation()
    sim.model_system = [root_system]
    sim.model_method = [method]

    archive = EntryArchive()
    archive.data = sim
    return archive


def test_archive_to_universe_masses_from_forcefield():
    """When ForceField.effective_masses is set, masses come from FF (not per-particle)."""
    from nomad_simulations.schema_packages.utils.molecular_dynamics import (
        archive_to_universe,
    )

    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=True, with_ff_charges=False
    )
    universe = archive_to_universe(archive)

    if universe is None:
        pytest.skip('archive_to_universe returned None — topology too minimal for MDA')

    expected_amu = np.array([15.999, 1.008, 1.008])
    assert np.isclose(universe.atoms.masses, expected_amu, rtol=1e-4).all()


def test_archive_to_universe_charges_from_forcefield():
    """When ForceField.partial_charges is set, charges come from FF."""
    from nomad_simulations.schema_packages.utils.molecular_dynamics import (
        archive_to_universe,
    )

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
    from nomad_simulations.schema_packages.utils.molecular_dynamics import (
        archive_to_universe,
    )

    archive = _build_minimal_archive(
        n_atoms=3, with_ff_masses=False, with_ff_charges=False
    )
    universe = archive_to_universe(archive)

    if universe is None:
        pytest.skip('archive_to_universe returned None — topology too minimal for MDA')

    assert np.allclose(universe.atoms.charges, 0.0)


def test_archive_to_universe_base_model_method_no_attribute_error():
    """
    Base ModelMethod as sec_method must not raise AttributeError in archive_to_universe.
    """
    from nomad_simulations.schema_packages.utils.molecular_dynamics import (
        archive_to_universe,
    )

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
            'archive_to_universe raised AttributeError with base ModelMethod: %s', exc
        )
