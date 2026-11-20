import numpy as np
import pytest
from nomad.datamodel import EntryArchive

from nomad_simulations.schema_packages.properties import (
    ElectronicBandStructure,
    ElectronicEigenvalues,
)
from nomad_simulations.schema_packages.variables import KLinePath, KPoints

from ..conftest import K_SAMPLING_POINTS, generate_electronic_band_structure
from . import logger


class TestElectronicBandStructure:
    """
    Test the `ElectronicBandStructure` class defined in `properties/band_structure.py`.
    """

    # ! Include this initial `test_default_quantities` method when testing your PhysicalProperty classes
    @pytest.mark.parametrize(
        'n_levels',
        [
            (None),
            (10),
        ],
    )
    def test_default_quantities(self, n_levels: int | None):
        """
        Test the default quantities assigned when creating an instance of the `ElectronicBandStructure` class.
        """
        electronic_band_structure = ElectronicBandStructure(n_levels=n_levels)
        assert (
            electronic_band_structure.iri
            == 'http://fairmat-nfdi.eu/taxonomy/ElectronicBandStructure'
        )

    def test_sibling_hierarchy(self):
        """
        Test that `ElectronicBandStructure` is a sibling of `ElectronicEigenvalues`, not a
        subclass: it carries neither the `k_points` axis nor the band-gap derivation, which
        require a full Brillouin-zone sampling.
        """
        assert not issubclass(ElectronicBandStructure, ElectronicEigenvalues)
        assert 'k_points' not in ElectronicBandStructure.m_def.all_sub_sections
        for derivation in (
            'order_eigenvalues',
            'resolve_homo_lumo_eigenvalues',
            'extract_band_gap',
            'emit_band_gap',
            'is_metallic',
            'extract_fermi_surface',
        ):
            assert not hasattr(ElectronicBandStructure, derivation)

    def test_k_path_axis(self):
        """
        Test that the `k_path` axis stores the sampled coordinates directly, with the
        high-symmetry points providing the segment structure.
        """
        electronic_band_structure = generate_electronic_band_structure()
        k_path = electronic_band_structure.k_path
        assert isinstance(k_path, KLinePath)
        assert isinstance(k_path, KPoints)
        assert np.asarray(k_path.points).shape == (8, 3)
        assert list(k_path.high_symmetry_labels) == ['Γ', 'R']
        assert list(k_path.high_symmetry_indices) == [0, 7]
        assert k_path.settings_ref is not None
        assert np.allclose(k_path.settings_ref.points, K_SAMPLING_POINTS)

    def test_normalize_does_not_derive_gap(self):
        """
        Test that normalizing a band structure derives neither the reference levels nor a band
        gap: path eigenvalues are not the reference-level producer.
        """
        electronic_band_structure = generate_electronic_band_structure(
            occupation=[[0, 2]] * 8,
        )
        outputs = electronic_band_structure.m_parent
        electronic_band_structure.normalize(EntryArchive(), logger)
        assert electronic_band_structure.highest_occupied is None
        assert electronic_band_structure.lowest_unoccupied is None
        assert len(outputs.electronic_band_gaps) == 0

    @pytest.mark.parametrize(
        'reciprocal_lattice_vectors, result',
        [
            (None, None),
            ([], None),
            ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        ],
    )
    def test_resolve_reciprocal_cell(
        self,
        reciprocal_lattice_vectors: list[list[float]] | None,
        result: list[list[float]] | None,
    ):
        """
        Test the `resolve_reciprocal_cell` method. This is done via the `normalize` function because `reciprocal_cell` is a
        `QuantityReference`, hence we need to assign it.
        """
        electronic_band_structure = generate_electronic_band_structure(
            reciprocal_lattice_vectors=reciprocal_lattice_vectors
        )
        # `normalize()` instead of `resolve_reciprocal_cell()` in order for refs to work
        electronic_band_structure.normalize(EntryArchive(), logger)
        reciprocal_cell = electronic_band_structure.reciprocal_cell
        if reciprocal_cell is not None:
            assert np.allclose(reciprocal_cell.magnitude, result)
        else:
            assert reciprocal_cell == result
