# docs-snippet: runnable
from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad_simulations.schema_packages.model_method import BSDFT, BrokenSymmetryCenter


def build_bs_dft_example() -> tuple[object, BSDFT]:
    """Create a plain DFT-like high-spin reference context and a BSDFT method."""
    fe1 = AtomsState(chemical_symbol='Fe', label='Fe1')
    fe2 = AtomsState(chemical_symbol='Fe', label='Fe2')

    method = BSDFT(
        determinant='unrestricted',
        is_spin_polarized=True,
        total_spin_projection=0,
    )
    method.spin_centers = [
        BrokenSymmetryCenter(atom_ref=fe1, spin_sign='up', label='site_a'),
        BrokenSymmetryCenter(atom_ref=fe2, spin_sign='down', label='site_b'),
    ]
    return fe1, method
