import numpy as np

from nomad_simulations.utils import cube_to_molecular_orbitals


def test_cube_to_molecular_orbitals(tmp_path):
    cube_text = """\
MO cube
generated for test
 1 0.0 0.0 0.0
 1 1.0 0.0 0.0
 1 0.0 1.0 0.0
 1 0.0 0.0 1.0
 1 0.0 0.0 0.0 0.0
 0.123
"""
    cube_path = tmp_path / 'simple.cube'
    cube_path.write_text(cube_text)

    mo, grid = cube_to_molecular_orbitals(
        cube_path,
        mo_index=5,
        spin=1,
        energy_ev=-5.0,
        occupation=2.0,
    )

    assert mo.n_mo == 1
    np.testing.assert_array_equal(mo.mo_spin, [1])
    np.testing.assert_allclose(mo.mo_energies, [-5.0])
    np.testing.assert_allclose(mo.mo_occupations, [2.0])
    np.testing.assert_array_equal(mo.mo_symmetry, ['5'])

    assert grid['values'].shape == (1, 1, 1)
    np.testing.assert_allclose(grid['values'], [[[0.123]]])
    np.testing.assert_allclose(grid['origin'], [0.0, 0.0, 0.0])
    np.testing.assert_allclose(grid['voxel_vectors'], np.eye(3))
    np.testing.assert_array_equal(grid['shape'], [1, 1, 1])
    np.testing.assert_array_equal(grid['atomic_numbers'], [1])
    np.testing.assert_allclose(grid['positions_bohr'], [[0.0, 0.0, 0.0]])
